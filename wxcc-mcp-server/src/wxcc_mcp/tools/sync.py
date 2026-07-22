"""Composite tool: sync_crm_to_address_book.

Reads the CRM source resource, lists the target address book's existing entries,
computes a create/update/delete diff, and (on approval) applies it. Matching is
by stable CRM id first, then by normalized E.164 number. Pruning (delete of
entries absent from the CRM source) is OFF by default.

The ``run`` coroutine accepts optional ``on_progress`` and ``on_log`` async
callbacks so the server can stream MCP progress notifications and client-facing
logs; the diff itself is a pure function for easy testing.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from ..api import entries as entries_api
from ..api.client import WxccApiClient
from ..logging_config import get_logger
from ..models.schemas import CrmContact, EntryItem, SyncAction, SyncCrmInput, SyncOutput
from ..resources import crm_contacts
from ._helpers import extract_items
from .entries import _entry_payload, _map_entry

logger = get_logger(__name__)

ProgressCb = Callable[[float, float, str], Awaitable[None]]
LogCb = Callable[[str, str], Awaitable[None]]


def compute_diff(
    contacts: list[CrmContact], existing: list[EntryItem], prune: bool
) -> list[SyncAction]:
    """Compute the sync plan from CRM contacts and existing entries (pure).

    Matches on CRM id first, then normalized E.164 number. Returns an ordered
    list of create/update/delete/skip actions.
    """
    by_crm = {e.crm_id: e for e in existing if e.crm_id}
    by_number = {e.number: e for e in existing if e.number}
    matched_ids: set[str] = set()
    actions: list[SyncAction] = []

    for contact in contacts:
        match = by_crm.get(contact.id) or by_number.get(contact.number)
        if match is None:
            actions.append(
                SyncAction(
                    action="create", name=contact.name, number=contact.number, crm_id=contact.id
                )
            )
            continue
        matched_ids.add(match.entry_id)
        if match.name != contact.name or match.number != contact.number:
            actions.append(
                SyncAction(
                    action="update",
                    entry_id=match.entry_id,
                    name=contact.name,
                    number=contact.number,
                    crm_id=contact.id,
                    reason="field changed",
                )
            )
        else:
            actions.append(
                SyncAction(
                    action="skip",
                    entry_id=match.entry_id,
                    name=contact.name,
                    number=contact.number,
                    crm_id=contact.id,
                    reason="unchanged",
                )
            )

    for entry in existing:
        if entry.entry_id in matched_ids:
            continue
        if prune:
            actions.append(
                SyncAction(
                    action="delete",
                    entry_id=entry.entry_id,
                    name=entry.name,
                    number=entry.number,
                    reason="absent from CRM source",
                )
            )
        else:
            actions.append(
                SyncAction(
                    action="skip",
                    entry_id=entry.entry_id,
                    name=entry.name,
                    number=entry.number,
                    reason="absent from CRM source (pruning disabled)",
                )
            )
    return actions


def _counts(actions: list[SyncAction]) -> dict[str, int]:
    """Tally actions by type."""
    tally = {"create": 0, "update": 0, "delete": 0, "skip": 0}
    for action in actions:
        tally[action.action] = tally.get(action.action, 0) + 1
    return tally


def deterministic_summary(output: SyncOutput) -> str:
    """Build a deterministic, human-readable summary of a sync result."""
    verb = "Applied" if output.committed else "Planned"
    return (
        f"{verb} sync for address book {output.address_book_id}: "
        f"{output.to_create} to create, {output.to_update} to update, "
        f"{output.to_delete} to delete, {output.skipped} unchanged/skipped."
    )


async def run(
    client: WxccApiClient,
    session_id: str,
    inp: SyncCrmInput,
    *,
    on_progress: ProgressCb | None = None,
    on_log: LogCb | None = None,
) -> SyncOutput:
    """Execute the CRM→address-book sync (dry-run unless ``confirm`` is set)."""
    logger.info(
        "tool_invoked",
        tool="sync_crm_to_address_book",
        address_book_id=inp.address_book_id,
        prune=inp.prune,
        dry_run=not inp.confirm,
    )

    contacts = [CrmContact(**c) for c in crm_contacts.get_contacts()]
    raw = await entries_api.list_entries(
        client, session_id, inp.org_id, inp.address_book_id, page_size=100
    )
    existing = [_map_entry(item) for item in extract_items(raw)]
    actions = compute_diff(contacts, existing, inp.prune)
    tally = _counts(actions)

    output = SyncOutput(
        address_book_id=inp.address_book_id,
        to_create=tally["create"],
        to_update=tally["update"],
        to_delete=tally["delete"],
        skipped=tally["skip"],
        actions=actions,
    )

    if not inp.confirm:
        output.dry_run = True
        output.committed = False
        output.message = deterministic_summary(output)
        return output

    changes = [a for a in actions if a.action in ("create", "update", "delete")]
    total = float(len(changes)) or 1.0
    done = 0.0
    for action in changes:
        if action.action == "create":
            payload = _entry_payload(action.name, action.number, action.crm_id)
            await entries_api.create_entry(
                client, session_id, inp.org_id, inp.address_book_id, payload
            )
        elif action.action == "update":
            payload = _entry_payload(action.name, action.number, None)
            await entries_api.update_entry(
                client, session_id, inp.org_id, inp.address_book_id, action.entry_id or "", payload
            )
        elif action.action == "delete":
            await entries_api.delete_entry(
                client, session_id, inp.org_id, inp.address_book_id, action.entry_id or ""
            )
        done += 1
        if on_progress is not None:
            await on_progress(done, total, f"{action.action} {action.name}")
        if on_log is not None:
            await on_log("info", f"{action.action}: {action.name} ({action.number})")

    output.dry_run = False
    output.committed = True
    output.message = deterministic_summary(output)
    return output
