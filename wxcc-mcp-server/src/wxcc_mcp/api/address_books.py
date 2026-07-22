"""WxCC Address Book API endpoints (Config family, target v2).

Thin async wrappers for CRUD operations on address books. Path constants live in
``config.py`` and are marked ``# VERIFY`` — confirm them against
developer.webex.com before going live. Address Book v1 is removed 2026-10-15;
these target v2.

Ref: https://developer.webex.com/webex-contact-center/docs/api/v1/address-book
"""

from __future__ import annotations

from typing import Any

from .. import config
from ..config import ApiFamily
from .client import WxccApiClient


async def list_address_books(
    client: WxccApiClient, session_id: str, org_id: str, *, max_results: int = 100
) -> Any:
    """List address books in an organization."""
    path = config.ADDRESS_BOOKS_PATH.format(org_id=org_id)
    params: dict[str, Any] = {"pageSize": min(max_results, 100)}  # VERIFY param name
    return await client.get(ApiFamily.CONFIG, path, session_id, params=params)


async def get_address_book(
    client: WxccApiClient, session_id: str, org_id: str, address_book_id: str
) -> Any:
    """Fetch a single address book by id."""
    path = config.ADDRESS_BOOK_BY_ID_PATH.format(org_id=org_id, address_book_id=address_book_id)
    return await client.get(ApiFamily.CONFIG, path, session_id)


async def create_address_book(
    client: WxccApiClient, session_id: str, org_id: str, payload: dict[str, Any]
) -> Any:
    """Create a new address book. Required body: name, parentType."""
    path = config.ADDRESS_BOOKS_PATH.format(org_id=org_id)
    return await client.post(ApiFamily.CONFIG, path, session_id, json_body=payload)


async def update_address_book(
    client: WxccApiClient,
    session_id: str,
    org_id: str,
    address_book_id: str,
    payload: dict[str, Any],
) -> Any:
    """Update an existing address book (name / description)."""
    path = config.ADDRESS_BOOK_BY_ID_PATH.format(org_id=org_id, address_book_id=address_book_id)
    return await client.put(ApiFamily.CONFIG, path, session_id, json_body=payload)


async def delete_address_book(
    client: WxccApiClient, session_id: str, org_id: str, address_book_id: str
) -> Any:
    """Delete an address book by id."""
    path = config.ADDRESS_BOOK_BY_ID_PATH.format(org_id=org_id, address_book_id=address_book_id)
    return await client.delete(ApiFamily.CONFIG, path, session_id)
