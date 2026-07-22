"""Tools: address book CRUD (list, get, create, update, delete).

Reads return typed summaries; writes follow the dry-run/elicitation safety
pattern. All response field names are marked ``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from ..api import address_books as api
from ..api.client import WxccApiClient
from ..logging_config import get_logger
from ..models.schemas import (
    AddressBookItem,
    CreateAddressBookInput,
    DeleteAddressBookInput,
    GetAddressBookInput,
    ListAddressBooksInput,
    ListAddressBooksOutput,
    UpdateAddressBookInput,
    WriteOutput,
)
from ._helpers import committed_response, dry_run_response, extract_items

logger = get_logger(__name__)


def _map_book(raw: dict[str, Any]) -> AddressBookItem:
    """Map a raw address book record to an :class:`AddressBookItem`. VERIFY fields."""
    return AddressBookItem(
        address_book_id=str(raw.get("id") or raw.get("addressBookId") or ""),  # VERIFY
        name=raw.get("name"),  # VERIFY
        description=raw.get("description"),  # VERIFY
        parent_type=raw.get("parentType"),  # VERIFY
    )


async def run_list(
    client: WxccApiClient, session_id: str, inp: ListAddressBooksInput
) -> ListAddressBooksOutput:
    """List address books in an organization."""
    logger.info("tool_invoked", tool="list_address_books", org_id=inp.org_id)
    raw = await api.list_address_books(client, session_id, inp.org_id, max_results=inp.max_results)
    books = [_map_book(item) for item in extract_items(raw)]
    return ListAddressBooksOutput(org_id=inp.org_id, total_returned=len(books), address_books=books)


async def run_get(
    client: WxccApiClient, session_id: str, inp: GetAddressBookInput
) -> AddressBookItem:
    """Get a single address book by id."""
    logger.info("tool_invoked", tool="get_address_book", address_book_id=inp.address_book_id)
    raw = await api.get_address_book(client, session_id, inp.org_id, inp.address_book_id)
    record = raw if isinstance(raw, dict) else {}
    return _map_book(record)


async def run_create(
    client: WxccApiClient, session_id: str, inp: CreateAddressBookInput
) -> WriteOutput:
    """Create an address book (dry-run unless ``confirm`` is set)."""
    logger.info("tool_invoked", tool="create_address_book", name=inp.name, dry_run=not inp.confirm)
    preview = {
        "action": "create_address_book",
        "name": inp.name,
        "parent_type": inp.parent_type,
        "description": inp.description,
    }
    if not inp.confirm:
        return WriteOutput(**dry_run_response(preview))
    payload: dict[str, Any] = {"name": inp.name, "parentType": inp.parent_type}  # VERIFY
    if inp.description is not None:
        payload["description"] = inp.description
    result = await api.create_address_book(client, session_id, inp.org_id, payload)
    rid = str(result.get("id") or "") if isinstance(result, dict) else ""
    return WriteOutput(**committed_response(result, rid))


async def run_update(
    client: WxccApiClient, session_id: str, inp: UpdateAddressBookInput
) -> WriteOutput:
    """Update an address book (dry-run unless ``confirm`` is set)."""
    logger.info(
        "tool_invoked",
        tool="update_address_book",
        address_book_id=inp.address_book_id,
        dry_run=not inp.confirm,
    )
    preview = {
        "action": "update_address_book",
        "address_book_id": inp.address_book_id,
        "name": inp.name,
        "description": inp.description,
    }
    if not inp.confirm:
        return WriteOutput(**dry_run_response(preview))
    payload: dict[str, Any] = {}
    if inp.name is not None:
        payload["name"] = inp.name
    if inp.description is not None:
        payload["description"] = inp.description
    result = await api.update_address_book(
        client, session_id, inp.org_id, inp.address_book_id, payload
    )
    return WriteOutput(**committed_response(result, inp.address_book_id))


async def run_delete(
    client: WxccApiClient, session_id: str, inp: DeleteAddressBookInput
) -> WriteOutput:
    """Delete an address book (dry-run unless ``confirm`` is set)."""
    logger.info(
        "tool_invoked",
        tool="delete_address_book",
        address_book_id=inp.address_book_id,
        dry_run=not inp.confirm,
    )
    preview = {
        "action": "delete_address_book",
        "address_book_id": inp.address_book_id,
        "warning": "This will permanently delete the address book and all its entries.",
    }
    if not inp.confirm:
        return WriteOutput(**dry_run_response(preview))
    result = await api.delete_address_book(client, session_id, inp.org_id, inp.address_book_id)
    return WriteOutput(**committed_response(result, inp.address_book_id))
