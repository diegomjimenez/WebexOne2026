"""WxCC Address Book Entry API endpoints (Config family).

Thin async wrappers for CRUD + bulk operations on an address book's entries.
Path constants live in ``config.py`` and are marked ``# VERIFY``. The list
endpoint supports ``search``, ``filter`` (RSQL), and ``attributes`` query
parameters plus pagination.
"""

from __future__ import annotations

from typing import Any

from .. import config
from ..config import ApiFamily
from .client import WxccApiClient


async def list_entries(
    client: WxccApiClient,
    session_id: str,
    org_id: str,
    address_book_id: str,
    *,
    search: str | None = None,
    filter: str | None = None,  # noqa: A002 - mirrors the API query param name
    attributes: str | None = None,
    page: int = 0,
    page_size: int = 100,
) -> Any:
    """List entries within an address book, with optional search/filter/attributes."""
    path = config.ADDRESS_BOOK_ENTRIES_PATH.format(org_id=org_id, address_book_id=address_book_id)
    params: dict[str, Any] = {"page": page, "pageSize": min(page_size, 100)}
    if search:
        params["search"] = search
    if filter:
        params["filter"] = filter
    if attributes:
        params["attributes"] = attributes
    return await client.get(ApiFamily.CONFIG, path, session_id, params=params)


async def get_entry(
    client: WxccApiClient, session_id: str, org_id: str, address_book_id: str, entry_id: str
) -> Any:
    """Fetch a single entry by id."""
    path = config.ADDRESS_BOOK_ENTRY_BY_ID_PATH.format(
        org_id=org_id, address_book_id=address_book_id, entry_id=entry_id
    )
    return await client.get(ApiFamily.CONFIG, path, session_id)


async def create_entry(
    client: WxccApiClient,
    session_id: str,
    org_id: str,
    address_book_id: str,
    payload: dict[str, Any],
) -> Any:
    """Create a new entry. Required body: name, number."""
    path = config.ADDRESS_BOOK_ENTRIES_PATH.format(org_id=org_id, address_book_id=address_book_id)
    return await client.post(ApiFamily.CONFIG, path, session_id, json_body=payload)


async def update_entry(
    client: WxccApiClient,
    session_id: str,
    org_id: str,
    address_book_id: str,
    entry_id: str,
    payload: dict[str, Any],
) -> Any:
    """Update an existing entry."""
    path = config.ADDRESS_BOOK_ENTRY_BY_ID_PATH.format(
        org_id=org_id, address_book_id=address_book_id, entry_id=entry_id
    )
    return await client.put(ApiFamily.CONFIG, path, session_id, json_body=payload)


async def delete_entry(
    client: WxccApiClient, session_id: str, org_id: str, address_book_id: str, entry_id: str
) -> Any:
    """Delete an entry by id."""
    path = config.ADDRESS_BOOK_ENTRY_BY_ID_PATH.format(
        org_id=org_id, address_book_id=address_book_id, entry_id=entry_id
    )
    return await client.delete(ApiFamily.CONFIG, path, session_id)


async def bulk_save_entries(
    client: WxccApiClient,
    session_id: str,
    org_id: str,
    address_book_id: str,
    payload: dict[str, Any],
) -> Any:
    """Bulk-save entries in a single request. VERIFY payload shape (upsert vs replace)."""
    path = config.ADDRESS_BOOK_ENTRIES_BULK_PATH.format(
        org_id=org_id, address_book_id=address_book_id
    )
    return await client.post(ApiFamily.CONFIG, path, session_id, json_body=payload)
