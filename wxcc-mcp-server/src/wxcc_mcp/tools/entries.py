"""Tools: address book entry CRUD + bulk save.

Reads return typed summaries; writes follow the dry-run/elicitation safety
pattern. Phone numbers are validated as E.164 at the schema layer. All response
field names are marked ``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from ..api import entries as api
from ..api.client import WxccApiClient
from ..logging_config import get_logger
from ..models.schemas import (
    BulkSaveEntriesInput,
    CreateEntryInput,
    DeleteEntryInput,
    EntryItem,
    GetEntryInput,
    ListEntriesInput,
    ListEntriesOutput,
    UpdateEntryInput,
    WriteOutput,
)
from ._helpers import committed_response, dry_run_response, extract_items

logger = get_logger(__name__)


def _map_entry(raw: dict[str, Any]) -> EntryItem:
    """Map a raw entry record to an :class:`EntryItem`. VERIFY field names."""
    return EntryItem(
        entry_id=str(raw.get("id") or raw.get("entryId") or ""),  # VERIFY
        name=raw.get("name"),  # VERIFY
        number=raw.get("number") or raw.get("phoneNumber"),  # VERIFY
        crm_id=raw.get("crmId"),  # VERIFY (stored as an attribute when synced from CRM)
    )


def _entry_payload(name: str | None, number: str | None, crm_id: str | None) -> dict[str, Any]:
    """Build an entry write payload from provided fields. VERIFY field names."""
    payload: dict[str, Any] = {}
    if name is not None:
        payload["name"] = name
    if number is not None:
        payload["number"] = number  # VERIFY (number vs phoneNumber)
    if crm_id is not None:
        payload["crmId"] = crm_id  # VERIFY (attribute used to store CRM id)
    return payload


async def run_list(
    client: WxccApiClient, session_id: str, inp: ListEntriesInput
) -> ListEntriesOutput:
    """List entries within an address book."""
    logger.info("tool_invoked", tool="list_entries", address_book_id=inp.address_book_id)
    raw = await api.list_entries(
        client,
        session_id,
        inp.org_id,
        inp.address_book_id,
        search=inp.search,
        filter=inp.filter,
        attributes=inp.attributes,
        page=inp.page,
        page_size=inp.page_size,
    )
    items = [_map_entry(item) for item in extract_items(raw)]
    return ListEntriesOutput(
        org_id=inp.org_id,
        address_book_id=inp.address_book_id,
        total_returned=len(items),
        entries=items,
    )


async def run_get(client: WxccApiClient, session_id: str, inp: GetEntryInput) -> EntryItem:
    """Get a single entry by id."""
    logger.info("tool_invoked", tool="get_entry", entry_id=inp.entry_id)
    raw = await api.get_entry(client, session_id, inp.org_id, inp.address_book_id, inp.entry_id)
    record = raw if isinstance(raw, dict) else {}
    return _map_entry(record)


async def run_create(client: WxccApiClient, session_id: str, inp: CreateEntryInput) -> WriteOutput:
    """Create an entry (dry-run unless ``confirm`` is set)."""
    logger.info("tool_invoked", tool="create_entry", dry_run=not inp.confirm)
    preview = {
        "action": "create_entry",
        "address_book_id": inp.address_book_id,
        "name": inp.name,
        "number": inp.number,
    }
    if not inp.confirm:
        return WriteOutput(**dry_run_response(preview))
    payload = _entry_payload(inp.name, inp.number, inp.crm_id)
    result = await api.create_entry(client, session_id, inp.org_id, inp.address_book_id, payload)
    rid = str(result.get("id") or "") if isinstance(result, dict) else ""
    return WriteOutput(**committed_response(result, rid))


async def run_update(client: WxccApiClient, session_id: str, inp: UpdateEntryInput) -> WriteOutput:
    """Update an entry (dry-run unless ``confirm`` is set)."""
    logger.info("tool_invoked", tool="update_entry", entry_id=inp.entry_id, dry_run=not inp.confirm)
    preview = {
        "action": "update_entry",
        "address_book_id": inp.address_book_id,
        "entry_id": inp.entry_id,
        "name": inp.name,
        "number": inp.number,
    }
    if not inp.confirm:
        return WriteOutput(**dry_run_response(preview))
    payload = _entry_payload(inp.name, inp.number, None)
    result = await api.update_entry(
        client, session_id, inp.org_id, inp.address_book_id, inp.entry_id, payload
    )
    return WriteOutput(**committed_response(result, inp.entry_id))


async def run_delete(client: WxccApiClient, session_id: str, inp: DeleteEntryInput) -> WriteOutput:
    """Delete an entry (dry-run unless ``confirm`` is set)."""
    logger.info("tool_invoked", tool="delete_entry", entry_id=inp.entry_id, dry_run=not inp.confirm)
    preview = {
        "action": "delete_entry",
        "address_book_id": inp.address_book_id,
        "entry_id": inp.entry_id,
        "warning": "This will permanently delete the entry.",
    }
    if not inp.confirm:
        return WriteOutput(**dry_run_response(preview))
    result = await api.delete_entry(
        client, session_id, inp.org_id, inp.address_book_id, inp.entry_id
    )
    return WriteOutput(**committed_response(result, inp.entry_id))


async def run_bulk_save(
    client: WxccApiClient, session_id: str, inp: BulkSaveEntriesInput
) -> WriteOutput:
    """Bulk-save entries (dry-run unless ``confirm`` is set)."""
    logger.info(
        "tool_invoked",
        tool="bulk_save_entries",
        address_book_id=inp.address_book_id,
        count=len(inp.entries),
        dry_run=not inp.confirm,
    )
    preview = {
        "action": "bulk_save_entries",
        "address_book_id": inp.address_book_id,
        "entry_count": len(inp.entries),
        "entries": [{"name": e.name, "number": e.number} for e in inp.entries],
    }
    if not inp.confirm:
        return WriteOutput(**dry_run_response(preview))
    payload: dict[str, Any] = {
        "entries": [_entry_payload(e.name, e.number, e.crm_id) for e in inp.entries]
    }  # VERIFY bulk payload shape
    result = await api.bulk_save_entries(
        client, session_id, inp.org_id, inp.address_book_id, payload
    )
    return WriteOutput(**committed_response(result, inp.address_book_id))
