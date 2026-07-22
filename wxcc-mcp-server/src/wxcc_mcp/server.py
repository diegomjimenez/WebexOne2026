"""MCP server entrypoint — WebexOne lab edition.

A deliberately small Webex Contact Center MCP server built to teach the Model
Context Protocol through one coherent scenario: **synchronizing CRM/directory
contacts into a WxCC Address Book and provisioning it for agents** by attaching
it to a Desktop Profile.

It demonstrates every core MCP primitive:

* **Tools** — address book / entry / desktop profile reads and confirm-gated writes.
* **Resources** — the CRM contact source, an address-book schema guide, and a
  write-safety guide the model can read.
* **Prompts** — templated flows that drive the sync and provisioning scenarios.
* **Elicitation** — interactive approval before any write commits.
* **Progress notifications** — per-entry updates during a sync.
* **Client-facing logging** — ``ctx.info``/``warning``/``error`` streamed to the client.
* **Sampling (optional)** — ask the client LLM to summarise a sync result.

Tokens are brokered per session by :class:`OAuthBroker` and never exposed to the
model. Tools translate typed API errors into plain-language messages. All API
calls use the single WxCC Config API family.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from .api.client import WxccApiClient
from .auth.oauth import OAuthBroker
from .config import get_settings
from .errors import WxccError
from .logging_config import configure_logging, get_logger
from .models.schemas import (
    AssignAddressBookInput,
    BulkSaveEntriesInput,
    CreateAddressBookInput,
    CreateEntryInput,
    DeleteAddressBookInput,
    DeleteEntryInput,
    EntryInput,
    GetAddressBookInput,
    GetAgentInput,
    GetDesktopProfileInput,
    GetEntryInput,
    ListAddressBooksInput,
    ListAgentsInput,
    ListDesktopProfilesInput,
    ListEntriesInput,
    ProfileAgentMapInput,
    SyncCrmInput,
    UpdateAddressBookInput,
    UpdateEntryInput,
)
from .prompts import provision_outbound_dialing as provision_prompt
from .prompts import sync_crm_to_address_book as sync_prompt
from .resources import address_book_schema_guide, crm_contacts, write_safety_guide
from .tools import address_books, agents, desktop_profiles, entries, sync
from .tools._common import translate_error

logger = get_logger(__name__)

mcp = FastMCP("wxcc-mcp-server")

_broker: OAuthBroker | None = None
_client: WxccApiClient | None = None


def _get_client() -> WxccApiClient:
    """Return the lazily-initialized broker-backed API client."""
    global _broker, _client
    if _broker is None:
        _broker = OAuthBroker()
    if _client is None:
        _client = WxccApiClient(_broker)
    return _client


def _session_id(ctx: Context | None) -> str:
    """Derive a per-session id from the MCP context.

    Falls back to a stable local id for single-user stdio deployments. A remote
    multi-user deployment MUST map each MCP session to a distinct broker session.
    """
    if ctx is not None:
        for attr in ("client_id", "session_id"):
            value = getattr(ctx, attr, None)
            if value:
                return str(value)
        session = getattr(ctx, "session", None)
        if session is not None and getattr(session, "session_id", None):
            return str(session.session_id)
    return "local-stdio-session"


async def _run_tool(coro_factory: Any, ctx: Context | None) -> dict[str, Any]:
    """Execute a tool coroutine, translating typed errors to plain language."""
    try:
        result = await coro_factory()
        return result.model_dump(mode="json")
    except WxccError as exc:
        return {"error": translate_error(exc)}
    except ValueError as exc:
        # E.164 / schema validation failures surface as a safe, plain message.
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# MCP primitive helpers (elicitation / progress / logging / sampling)
#
# Every helper is defensive: MCP clients differ in which primitives they
# support, so unsupported calls degrade gracefully instead of crashing a tool.
# ---------------------------------------------------------------------------


class _ApproveWrite(BaseModel):
    """Schema for the elicited write-confirmation response."""

    approve: bool = Field(description="Approve and commit this write action?")


async def _emit_log(ctx: Context | None, level: str, message: str) -> None:
    """Stream a client-facing log message; no-op if unsupported."""
    if ctx is None:
        return
    try:
        fn = getattr(ctx, level, None)
        if fn is not None:
            await fn(message)
    except Exception:  # noqa: BLE001 - logging must never break a tool
        pass


async def _emit_progress(
    ctx: Context | None, progress: float, total: float, message: str | None = None
) -> None:
    """Send a progress notification; no-op if unsupported."""
    if ctx is None:
        return
    try:
        await ctx.report_progress(progress=progress, total=total, message=message)
    except TypeError:
        try:
            await ctx.report_progress(progress, total)
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        pass


async def _should_commit(ctx: Context | None, summary: str, confirm_flag: bool) -> bool:
    """Decide whether a write should commit.

    Prefers interactive elicitation. If the client does not support elicitation
    (or it errors), falls back to the explicit ``confirm`` argument so the tool
    still works — and stays safe by defaulting to *not* committing.
    """
    if ctx is not None:
        try:
            result = await ctx.elicit(
                message=f"Confirm write action: {summary}", schema=_ApproveWrite
            )
            action = getattr(result, "action", None)
            if action == "accept":
                data = getattr(result, "data", None)
                return bool(getattr(data, "approve", False))
            if action in ("decline", "cancel"):
                return False
        except Exception:  # noqa: BLE001 - fall back to the confirm flag
            pass
    return bool(confirm_flag)


async def _maybe_summarize(ctx: Context | None, findings: dict[str, Any]) -> str | None:
    """Optionally ask the client's LLM to summarise a sync result (sampling).

    Fully guarded: returns ``None`` if sampling is unavailable or errors, in
    which case callers use their own deterministic summary.
    """
    if ctx is None:
        return None
    try:
        from mcp.types import SamplingMessage, TextContent

        session = getattr(ctx, "session", None)
        create_message = getattr(session, "create_message", None)
        if create_message is None:
            return None
        prompt = (
            "In one or two sentences, summarise this WxCC address book sync "
            f"result for an administrator:\n{json.dumps(findings, indent=2)}"
        )
        result = await create_message(
            messages=[SamplingMessage(role="user", content=TextContent(type="text", text=prompt))],
            max_tokens=200,
        )
        content = getattr(result, "content", None)
        text = getattr(content, "text", None)
        return str(text) if text else None
    except Exception:  # noqa: BLE001 - sampling is optional
        return None


# ---------------------------------------------------------------------------
# Address book tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def tool_list_address_books(
    org_id: str, max_results: int = 100, ctx: Context = None
) -> dict[str, Any]:
    """List address books in a WxCC organization (read-only)."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: address_books.run_list(
            client, sid, ListAddressBooksInput(org_id=org_id, max_results=max_results)
        ),
        ctx,
    )


@mcp.tool()
async def tool_get_address_book(
    org_id: str, address_book_id: str, ctx: Context = None
) -> dict[str, Any]:
    """Get a single address book by id (read-only)."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: address_books.run_get(
            client, sid, GetAddressBookInput(org_id=org_id, address_book_id=address_book_id)
        ),
        ctx,
    )


@mcp.tool()
async def tool_create_address_book(
    org_id: str,
    name: str,
    parent_type: str,
    description: str | None = None,
    confirm: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create an address book (elicitation-gated)."""
    client = _get_client()
    sid = _session_id(ctx)
    commit = await _should_commit(ctx, f"create address book {name}", confirm)
    await _emit_log(ctx, "info", f"create_address_book name={name} commit={commit}")
    return await _run_tool(
        lambda: address_books.run_create(
            client,
            sid,
            CreateAddressBookInput(
                org_id=org_id,
                name=name,
                parent_type=parent_type,
                description=description,
                confirm=commit,
            ),
        ),
        ctx,
    )


@mcp.tool()
async def tool_update_address_book(
    org_id: str,
    address_book_id: str,
    name: str | None = None,
    description: str | None = None,
    confirm: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an address book (elicitation-gated)."""
    client = _get_client()
    sid = _session_id(ctx)
    commit = await _should_commit(ctx, f"update address book {address_book_id}", confirm)
    await _emit_log(ctx, "info", f"update_address_book id={address_book_id} commit={commit}")
    return await _run_tool(
        lambda: address_books.run_update(
            client,
            sid,
            UpdateAddressBookInput(
                org_id=org_id,
                address_book_id=address_book_id,
                name=name,
                description=description,
                confirm=commit,
            ),
        ),
        ctx,
    )


@mcp.tool()
async def tool_delete_address_book(
    org_id: str, address_book_id: str, confirm: bool = False, ctx: Context = None
) -> dict[str, Any]:
    """Delete an address book and all its entries (elicitation-gated, HIGH risk)."""
    client = _get_client()
    sid = _session_id(ctx)
    commit = await _should_commit(ctx, f"delete address book {address_book_id}", confirm)
    await _emit_log(ctx, "warning", f"delete_address_book id={address_book_id} commit={commit}")
    return await _run_tool(
        lambda: address_books.run_delete(
            client,
            sid,
            DeleteAddressBookInput(org_id=org_id, address_book_id=address_book_id, confirm=commit),
        ),
        ctx,
    )


# ---------------------------------------------------------------------------
# Entry tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def tool_list_entries(
    org_id: str,
    address_book_id: str,
    search: str | None = None,
    filter: str | None = None,
    attributes: str | None = None,
    page: int = 0,
    page_size: int = 100,
    ctx: Context = None,
) -> dict[str, Any]:
    """List entries in an address book with optional search/filter/attributes (read-only)."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: entries.run_list(
            client,
            sid,
            ListEntriesInput(
                org_id=org_id,
                address_book_id=address_book_id,
                search=search,
                filter=filter,
                attributes=attributes,
                page=page,
                page_size=page_size,
            ),
        ),
        ctx,
    )


@mcp.tool()
async def tool_get_entry(
    org_id: str, address_book_id: str, entry_id: str, ctx: Context = None
) -> dict[str, Any]:
    """Get a single address book entry by id (read-only)."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: entries.run_get(
            client,
            sid,
            GetEntryInput(org_id=org_id, address_book_id=address_book_id, entry_id=entry_id),
        ),
        ctx,
    )


@mcp.tool()
async def tool_create_entry(
    org_id: str,
    address_book_id: str,
    name: str,
    number: str,
    crm_id: str | None = None,
    confirm: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Create an address book entry with an E.164 number (elicitation-gated)."""
    client = _get_client()
    sid = _session_id(ctx)
    commit = await _should_commit(ctx, f"create entry {name} ({number})", confirm)
    await _emit_log(ctx, "info", f"create_entry name={name} commit={commit}")
    return await _run_tool(
        lambda: entries.run_create(
            client,
            sid,
            CreateEntryInput(
                org_id=org_id,
                address_book_id=address_book_id,
                name=name,
                number=number,
                crm_id=crm_id,
                confirm=commit,
            ),
        ),
        ctx,
    )


@mcp.tool()
async def tool_update_entry(
    org_id: str,
    address_book_id: str,
    entry_id: str,
    name: str | None = None,
    number: str | None = None,
    confirm: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update an address book entry (elicitation-gated)."""
    client = _get_client()
    sid = _session_id(ctx)
    commit = await _should_commit(ctx, f"update entry {entry_id}", confirm)
    await _emit_log(ctx, "info", f"update_entry id={entry_id} commit={commit}")
    return await _run_tool(
        lambda: entries.run_update(
            client,
            sid,
            UpdateEntryInput(
                org_id=org_id,
                address_book_id=address_book_id,
                entry_id=entry_id,
                name=name,
                number=number,
                confirm=commit,
            ),
        ),
        ctx,
    )


@mcp.tool()
async def tool_delete_entry(
    org_id: str, address_book_id: str, entry_id: str, confirm: bool = False, ctx: Context = None
) -> dict[str, Any]:
    """Delete an address book entry (elicitation-gated, HIGH risk)."""
    client = _get_client()
    sid = _session_id(ctx)
    commit = await _should_commit(ctx, f"delete entry {entry_id}", confirm)
    await _emit_log(ctx, "warning", f"delete_entry id={entry_id} commit={commit}")
    return await _run_tool(
        lambda: entries.run_delete(
            client,
            sid,
            DeleteEntryInput(
                org_id=org_id, address_book_id=address_book_id, entry_id=entry_id, confirm=commit
            ),
        ),
        ctx,
    )


@mcp.tool()
async def tool_bulk_save_entries(
    org_id: str,
    address_book_id: str,
    entries_payload: list[dict[str, Any]],
    confirm: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Bulk-save entries into an address book (elicitation-gated).

    ``entries_payload`` is a list of ``{"name", "number", "crm_id"?}`` objects;
    each number must be valid E.164.
    """
    client = _get_client()
    sid = _session_id(ctx)
    commit = await _should_commit(ctx, f"bulk save {len(entries_payload)} entries", confirm)
    await _emit_log(ctx, "info", f"bulk_save_entries count={len(entries_payload)} commit={commit}")
    return await _run_tool(
        lambda: entries.run_bulk_save(
            client,
            sid,
            BulkSaveEntriesInput(
                org_id=org_id,
                address_book_id=address_book_id,
                entries=[EntryInput(**e) for e in entries_payload],
                confirm=commit,
            ),
        ),
        ctx,
    )


# ---------------------------------------------------------------------------
# Desktop profile + agent tools (reads + gated assignment)
# ---------------------------------------------------------------------------


@mcp.tool()
async def tool_list_desktop_profiles(
    org_id: str, max_results: int = 100, ctx: Context = None
) -> dict[str, Any]:
    """List desktop profiles in a WxCC organization (read-only)."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: desktop_profiles.run_list(
            client, sid, ListDesktopProfilesInput(org_id=org_id, max_results=max_results)
        ),
        ctx,
    )


@mcp.tool()
async def tool_get_desktop_profile(
    org_id: str, profile_id: str, ctx: Context = None
) -> dict[str, Any]:
    """Get a single desktop profile by id (read-only)."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: desktop_profiles.run_get(
            client, sid, GetDesktopProfileInput(org_id=org_id, profile_id=profile_id)
        ),
        ctx,
    )


@mcp.tool()
async def tool_list_agents(
    org_id: str, max_results: int = 100, ctx: Context = None
) -> dict[str, Any]:
    """List agents (users) with their desktop profile assignment (read-only)."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: agents.run_list(
            client, sid, ListAgentsInput(org_id=org_id, max_results=max_results)
        ),
        ctx,
    )


@mcp.tool()
async def tool_get_agent(org_id: str, identifier: str, ctx: Context = None) -> dict[str, Any]:
    """Get a single agent (user) by id (read-only)."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: agents.run_get(client, sid, GetAgentInput(org_id=org_id, identifier=identifier)),
        ctx,
    )


@mcp.tool()
async def tool_map_profiles_to_agents(
    org_id: str, max_results: int = 100, ctx: Context = None
) -> dict[str, Any]:
    """Map each desktop profile to the agents assigned to it (read-only).

    Shows which agents would gain access if an address book is assigned to a
    given profile.
    """
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: agents.run_map_profiles_to_agents(
            client, sid, ProfileAgentMapInput(org_id=org_id, max_results=max_results)
        ),
        ctx,
    )


@mcp.tool()
async def tool_assign_address_book_to_profile(
    org_id: str, profile_id: str, address_book_id: str, confirm: bool = False, ctx: Context = None
) -> dict[str, Any]:
    """Assign an address book to a desktop profile (elicitation-gated).

    Changes only ``addressBookId``; all other (non-deprecated) profile fields are
    preserved.
    """
    client = _get_client()
    sid = _session_id(ctx)
    commit = await _should_commit(
        ctx, f"assign address book {address_book_id} to profile {profile_id}", confirm
    )
    await _emit_log(
        ctx,
        "info",
        f"assign_address_book profile={profile_id} book={address_book_id} commit={commit}",
    )
    return await _run_tool(
        lambda: desktop_profiles.run_assign_address_book(
            client,
            sid,
            AssignAddressBookInput(
                org_id=org_id,
                profile_id=profile_id,
                address_book_id=address_book_id,
                confirm=commit,
            ),
        ),
        ctx,
    )


# ---------------------------------------------------------------------------
# Composite sync tool
# ---------------------------------------------------------------------------


@mcp.tool()
async def tool_sync_crm_to_address_book(
    org_id: str,
    address_book_id: str,
    prune: bool = False,
    summarize: bool = False,
    confirm: bool = False,
    ctx: Context = None,
) -> dict[str, Any]:
    """Sync CRM contacts into an address book (elicitation-gated composite).

    Reads the CRM source, diffs it against existing entries, and returns a
    dry-run preview (counts to create/update/delete). On approval it applies the
    plan, streaming per-entry progress and logs. ``prune`` (delete entries absent
    from the CRM source) is OFF by default. When ``summarize`` is set and the
    client supports sampling, a natural-language summary is added.
    """
    client = _get_client()
    sid = _session_id(ctx)
    summary = f"sync CRM into address book {address_book_id}"
    if prune:
        summary += " (with pruning — deletes entries absent from CRM)"
    commit = await _should_commit(ctx, summary, confirm)
    await _emit_log(ctx, "info", f"sync_crm_to_address_book book={address_book_id} commit={commit}")

    async def _progress(done: float, total: float, message: str) -> None:
        await _emit_progress(ctx, done, total, message)

    async def _log(level: str, message: str) -> None:
        await _emit_log(ctx, level, message)

    result = await _run_tool(
        lambda: sync.run(
            client,
            sid,
            SyncCrmInput(
                org_id=org_id,
                address_book_id=address_book_id,
                prune=prune,
                summarize=summarize,
                confirm=commit,
            ),
            on_progress=_progress,
            on_log=_log,
        ),
        ctx,
    )
    if "error" not in result and summarize:
        llm_summary = await _maybe_summarize(ctx, result)
        if llm_summary:
            result["llm_summary"] = llm_summary
    return result


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource(crm_contacts.RESOURCE_URI)
def resource_crm_contacts() -> str:
    """The CRM/directory contact export used as the sync source of truth."""
    return json.dumps(crm_contacts.as_dict(), indent=2)


@mcp.resource(address_book_schema_guide.RESOURCE_URI)
def resource_address_book_schema_guide() -> str:
    """Rules for address books and entries: naming, E.164, parentType."""
    return json.dumps(address_book_schema_guide.as_dict(), indent=2)


@mcp.resource(write_safety_guide.RESOURCE_URI)
def resource_write_safety_guide() -> str:
    """Policies and patterns for safely executing WxCC write operations."""
    return json.dumps(write_safety_guide.as_dict(), indent=2)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt(name=sync_prompt.PROMPT_NAME, description=sync_prompt.PROMPT_DESCRIPTION)
def prompt_sync_crm_to_address_book(
    org_id: str, address_book_id: str = "", prune: bool = False
) -> str:
    """Render the CRM→address-book sync walkthrough prompt."""
    return sync_prompt.build_prompt(org_id=org_id, address_book_id=address_book_id, prune=prune)


@mcp.prompt(name=provision_prompt.PROMPT_NAME, description=provision_prompt.PROMPT_DESCRIPTION)
def prompt_provision_outbound_dialing(
    org_id: str, book_name: str = "", profile_id: str = ""
) -> str:
    """Render the end-to-end outbound-dialing provisioning prompt."""
    return provision_prompt.build_prompt(org_id=org_id, book_name=book_name, profile_id=profile_id)


def main() -> None:
    """Configure logging and run the server over stdio."""
    settings = get_settings()
    configure_logging(settings.log_level, log_file=settings.log_file)
    logger.info("wxcc_mcp_server_starting", transport="stdio")
    mcp.run()


if __name__ == "__main__":
    main()
