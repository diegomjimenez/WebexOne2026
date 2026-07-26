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
* **Sampling (optional)** — ask the client LLM to summarise a sync result.

Observability is delivered entirely through **stderr-native structured logging**
(structlog → stderr, and optionally a log file). Each tool invocation emits
correlated ``tool.received`` / ``tool.result`` / ``tool.error`` events sharing a
short ``request_id``. In-protocol client logging (``notifications/message``) is
intentionally **not** used: it was deprecated by the Model Context Protocol in
`SEP-2577 <https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging>`_
(2026-07-28), which directs new servers to log to stderr where the host captures
it automatically.

Tokens are brokered per session by :class:`OAuthBroker` and never exposed to the
model. Tools translate typed API errors into plain-language messages. All API
calls use the single WxCC Config API family.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from ._runtime import (
    emit_progress,
    get_client,
    maybe_summarize,
    run_tool,
    session_id,
    should_commit,
)
from .config import get_settings
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
from .icon import SERVER_ICON
from .tools import address_books, agents, desktop_profiles, entries, sync

logger = get_logger(__name__)

mcp = FastMCP("wxcc-mcp-server", icons=[SERVER_ICON])


# ===========================================================================
# Anatomy of an MCP tool  (read this once — every tool below has this shape)
#
# A tool is just an async function registered with @mcp.tool(). Each one makes
# the same three moves:
#
#   1. resolve the per-session Webex client            → get_client()
#   2. map the MCP arguments to a typed *Input and      → address_books.run_list(
#      call the matching function in tools/                  client, sid, SomeInput(...))
#   3. hand that call to run_tool(), which tags it with  → run_tool(lambda: ..., ctx,
#      a request_id, times it, logs received/result/         tool_name=..., intent=...)
#      error, and translates Webex errors to plain text.
#
# Why the `lambda:`? It DEFERS the call so run_tool() can start its timer and
# bind the correlation id *before* the work runs, then await it. Read one tool
# and you've read them all. The machinery lives in `_runtime.py` — read it second.
# ===========================================================================

# ---------------------------------------------------------------------------
# Address book tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def tool_list_address_books(
    org_id: str, max_results: int = 100, ctx: Context = None
) -> dict[str, Any]:
    """List address books in a WxCC organization (read-only)."""
    client = get_client()
    sid = session_id(ctx)
    return await run_tool(
        lambda: address_books.run_list(
            client, sid, ListAddressBooksInput(org_id=org_id, max_results=max_results)
        ),
        ctx,
        tool_name="list_address_books",
        intent=f"listing address books for org {org_id}",
    )


@mcp.tool()
async def tool_get_address_book(
    org_id: str, address_book_id: str, ctx: Context = None
) -> dict[str, Any]:
    """Get a single address book by id (read-only)."""
    client = get_client()
    sid = session_id(ctx)
    return await run_tool(
        lambda: address_books.run_get(
            client, sid, GetAddressBookInput(org_id=org_id, address_book_id=address_book_id)
        ),
        ctx,
        tool_name="get_address_book",
        intent=f"reading address book {address_book_id}",
    )


# --- Anatomy of a *write* tool -------------------------------------------
# Writes add one move before the three above: should_commit() asks the user to
# approve (via MCP elicitation), falling back to the explicit `confirm` flag.
# Without approval the underlying tools/ function returns a dry-run preview and
# nothing hits Webex; only an approved call commits. Every write tool below
# follows this same gate.
# -------------------------------------------------------------------------


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
    client = get_client()
    sid = session_id(ctx)
    commit = await should_commit(ctx, f"create address book {name}", confirm)
    return await run_tool(
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
        tool_name="create_address_book",
        intent=f"create address book '{name}' (commit={commit})",
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
    client = get_client()
    sid = session_id(ctx)
    commit = await should_commit(ctx, f"update address book {address_book_id}", confirm)
    return await run_tool(
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
        tool_name="update_address_book",
        intent=f"update address book {address_book_id} (commit={commit})",
    )


@mcp.tool()
async def tool_delete_address_book(
    org_id: str, address_book_id: str, confirm: bool = False, ctx: Context = None
) -> dict[str, Any]:
    """Delete an address book and all its entries (elicitation-gated, HIGH risk)."""
    client = get_client()
    sid = session_id(ctx)
    commit = await should_commit(ctx, f"delete address book {address_book_id}", confirm)
    return await run_tool(
        lambda: address_books.run_delete(
            client,
            sid,
            DeleteAddressBookInput(org_id=org_id, address_book_id=address_book_id, confirm=commit),
        ),
        ctx,
        tool_name="delete_address_book",
        intent=f"delete address book {address_book_id} (commit={commit})",
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
    client = get_client()
    sid = session_id(ctx)
    return await run_tool(
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
        tool_name="list_entries",
        intent=f"listing entries in address book {address_book_id}",
    )


@mcp.tool()
async def tool_get_entry(
    org_id: str, address_book_id: str, entry_id: str, ctx: Context = None
) -> dict[str, Any]:
    """Get a single address book entry by id (read-only)."""
    client = get_client()
    sid = session_id(ctx)
    return await run_tool(
        lambda: entries.run_get(
            client,
            sid,
            GetEntryInput(org_id=org_id, address_book_id=address_book_id, entry_id=entry_id),
        ),
        ctx,
        tool_name="get_entry",
        intent=f"reading entry {entry_id}",
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
    client = get_client()
    sid = session_id(ctx)
    commit = await should_commit(ctx, f"create entry {name} ({number})", confirm)
    return await run_tool(
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
        tool_name="create_entry",
        intent=f"create entry '{name}' ({number}) (commit={commit})",
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
    client = get_client()
    sid = session_id(ctx)
    commit = await should_commit(ctx, f"update entry {entry_id}", confirm)
    return await run_tool(
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
        tool_name="update_entry",
        intent=f"update entry {entry_id} (commit={commit})",
    )


@mcp.tool()
async def tool_delete_entry(
    org_id: str, address_book_id: str, entry_id: str, confirm: bool = False, ctx: Context = None
) -> dict[str, Any]:
    """Delete an address book entry (elicitation-gated, HIGH risk)."""
    client = get_client()
    sid = session_id(ctx)
    commit = await should_commit(ctx, f"delete entry {entry_id}", confirm)
    return await run_tool(
        lambda: entries.run_delete(
            client,
            sid,
            DeleteEntryInput(
                org_id=org_id, address_book_id=address_book_id, entry_id=entry_id, confirm=commit
            ),
        ),
        ctx,
        tool_name="delete_entry",
        intent=f"delete entry {entry_id} (commit={commit})",
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
    client = get_client()
    sid = session_id(ctx)
    commit = await should_commit(ctx, f"bulk save {len(entries_payload)} entries", confirm)
    return await run_tool(
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
        tool_name="bulk_save_entries",
        intent=f"bulk save {len(entries_payload)} entries (commit={commit})",
    )


# ---------------------------------------------------------------------------
# Desktop profile + agent tools (reads + gated assignment)
# ---------------------------------------------------------------------------


@mcp.tool()
async def tool_list_desktop_profiles(
    org_id: str, max_results: int = 100, ctx: Context = None
) -> dict[str, Any]:
    """List desktop profiles in a WxCC organization (read-only)."""
    client = get_client()
    sid = session_id(ctx)
    return await run_tool(
        lambda: desktop_profiles.run_list(
            client, sid, ListDesktopProfilesInput(org_id=org_id, max_results=max_results)
        ),
        ctx,
        tool_name="list_desktop_profiles",
        intent=f"listing desktop profiles for org {org_id}",
    )


@mcp.tool()
async def tool_get_desktop_profile(
    org_id: str, profile_id: str, ctx: Context = None
) -> dict[str, Any]:
    """Get a single desktop profile by id (read-only)."""
    client = get_client()
    sid = session_id(ctx)
    return await run_tool(
        lambda: desktop_profiles.run_get(
            client, sid, GetDesktopProfileInput(org_id=org_id, profile_id=profile_id)
        ),
        ctx,
        tool_name="get_desktop_profile",
        intent=f"reading desktop profile {profile_id}",
    )


@mcp.tool()
async def tool_list_agents(
    org_id: str, max_results: int = 100, ctx: Context = None
) -> dict[str, Any]:
    """List agents (users) with their desktop profile assignment (read-only)."""
    client = get_client()
    sid = session_id(ctx)
    return await run_tool(
        lambda: agents.run_list(
            client, sid, ListAgentsInput(org_id=org_id, max_results=max_results)
        ),
        ctx,
        tool_name="list_agents",
        intent=f"listing agents for org {org_id}",
    )


@mcp.tool()
async def tool_get_agent(org_id: str, identifier: str, ctx: Context = None) -> dict[str, Any]:
    """Get a single agent (user) by id (read-only)."""
    client = get_client()
    sid = session_id(ctx)
    return await run_tool(
        lambda: agents.run_get(client, sid, GetAgentInput(org_id=org_id, identifier=identifier)),
        ctx,
        tool_name="get_agent",
        intent=f"reading agent {identifier}",
    )


@mcp.tool()
async def tool_map_profiles_to_agents(
    org_id: str, max_results: int = 100, ctx: Context = None
) -> dict[str, Any]:
    """Map each desktop profile to the agents assigned to it (read-only).

    Shows which agents would gain access if an address book is assigned to a
    given profile.
    """
    client = get_client()
    sid = session_id(ctx)
    return await run_tool(
        lambda: agents.run_map_profiles_to_agents(
            client, sid, ProfileAgentMapInput(org_id=org_id, max_results=max_results)
        ),
        ctx,
        tool_name="map_profiles_to_agents",
        intent=f"mapping profiles to agents for org {org_id}",
    )


@mcp.tool()
async def tool_assign_address_book_to_profile(
    org_id: str, profile_id: str, address_book_id: str, confirm: bool = False, ctx: Context = None
) -> dict[str, Any]:
    """Assign an address book to a desktop profile (elicitation-gated).

    Changes only ``addressBookId``; all other (non-deprecated) profile fields are
    preserved.
    """
    client = get_client()
    sid = session_id(ctx)
    commit = await should_commit(
        ctx, f"assign address book {address_book_id} to profile {profile_id}", confirm
    )
    return await run_tool(
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
        tool_name="assign_address_book_to_profile",
        intent=f"assign book {address_book_id} to profile {profile_id} (commit={commit})",
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
    client = get_client()
    sid = session_id(ctx)
    summary = f"sync CRM into address book {address_book_id}"
    if prune:
        summary += " (with pruning — deletes entries absent from CRM)"
    commit = await should_commit(ctx, summary, confirm)

    async def _progress(done: float, total: float, message: str) -> None:
        await emit_progress(ctx, done, total, message)

    async def _log(_level: str, message: str) -> None:
        # Per-entry sync events go to the stderr-native structured stream; they
        # inherit the invocation's request_id via contextvars (bound in run_tool).
        logger.info("sync.entry", detail=message)

    result = await run_tool(
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
        tool_name="sync_crm_to_address_book",
        intent=f"sync CRM into address book {address_book_id} (commit={commit})",
    )
    if "error" not in result and summarize:
        llm_summary = await maybe_summarize(ctx, result)
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
    logger.debug("wxcc_mcp_server_starting", transport="stdio")
    mcp.run()


if __name__ == "__main__":
    main()
