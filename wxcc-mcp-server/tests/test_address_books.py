"""Tests for the address book CRUD tools (mocked API)."""

from __future__ import annotations

from wxcc_mcp.models.schemas import (
    CreateAddressBookInput,
    DeleteAddressBookInput,
    GetAddressBookInput,
    ListAddressBooksInput,
    UpdateAddressBookInput,
)
from wxcc_mcp.tools import address_books

ORG = "org1"
SID = "s1"


async def test_list_address_books(client):
    out = await address_books.run_list(client, SID, ListAddressBooksInput(org_id=ORG))
    assert out.total_returned == 2
    ids = {b.address_book_id for b in out.address_books}
    assert ids == {"ab1", "ab2"}


async def test_get_address_book(client):
    out = await address_books.run_get(
        client, SID, GetAddressBookInput(org_id=ORG, address_book_id="ab1")
    )
    assert out.address_book_id == "ab1"
    assert out.parent_type == "CUSTOMER"


async def test_create_address_book_dry_run(client):
    out = await address_books.run_create(
        client, SID, CreateAddressBookInput(org_id=ORG, name="New Book", parent_type="CUSTOMER")
    )
    assert out.dry_run is True
    assert out.committed is False
    assert out.preview["name"] == "New Book"


async def test_create_address_book_commit(client):
    out = await address_books.run_create(
        client,
        SID,
        CreateAddressBookInput(org_id=ORG, name="New Book", parent_type="CUSTOMER", confirm=True),
    )
    assert out.committed is True
    assert out.resource_id == "ab-new"


async def test_update_address_book_commit(client):
    out = await address_books.run_update(
        client,
        SID,
        UpdateAddressBookInput(org_id=ORG, address_book_id="ab1", name="Renamed", confirm=True),
    )
    assert out.committed is True
    assert out.resource_id == "ab1"


async def test_delete_address_book_dry_run_then_commit(client):
    preview = await address_books.run_delete(
        client, SID, DeleteAddressBookInput(org_id=ORG, address_book_id="ab1")
    )
    assert preview.dry_run is True
    assert "warning" in preview.preview

    out = await address_books.run_delete(
        client, SID, DeleteAddressBookInput(org_id=ORG, address_book_id="ab1", confirm=True)
    )
    assert out.committed is True
