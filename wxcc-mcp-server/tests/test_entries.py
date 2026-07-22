"""Tests for the address book entry CRUD + bulk-save tools (mocked API)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from wxcc_mcp.models.schemas import (
    BulkSaveEntriesInput,
    CreateEntryInput,
    DeleteEntryInput,
    EntryInput,
    GetEntryInput,
    ListEntriesInput,
    UpdateEntryInput,
)
from wxcc_mcp.tools import entries

ORG = "org1"
SID = "s1"
AB = "ab1"


async def test_list_entries(client):
    out = await entries.run_list(client, SID, ListEntriesInput(org_id=ORG, address_book_id=AB))
    assert out.total_returned == 3
    assert {e.entry_id for e in out.entries} == {"e1", "e2", "e3"}


async def test_get_entry(client):
    out = await entries.run_get(
        client, SID, GetEntryInput(org_id=ORG, address_book_id=AB, entry_id="e1")
    )
    assert out.entry_id == "e1"
    assert out.crm_id == "crm-1001"


async def test_create_entry_dry_run_then_commit(client):
    preview = await entries.run_create(
        client,
        SID,
        CreateEntryInput(org_id=ORG, address_book_id=AB, name="New", number="+14155559999"),
    )
    assert preview.dry_run is True

    out = await entries.run_create(
        client,
        SID,
        CreateEntryInput(
            org_id=ORG, address_book_id=AB, name="New", number="+14155559999", confirm=True
        ),
    )
    assert out.committed is True
    assert out.resource_id == "e-new"


async def test_create_entry_normalizes_number():
    inp = CreateEntryInput(org_id=ORG, address_book_id=AB, name="X", number="+1 (415) 555-0101")
    assert inp.number == "+14155550101"


async def test_create_entry_rejects_invalid_number():
    with pytest.raises(ValidationError):
        CreateEntryInput(org_id=ORG, address_book_id=AB, name="X", number="not-a-number")


async def test_update_entry_commit(client):
    out = await entries.run_update(
        client,
        SID,
        UpdateEntryInput(
            org_id=ORG, address_book_id=AB, entry_id="e1", name="Renamed", confirm=True
        ),
    )
    assert out.committed is True
    assert out.resource_id == "e1"


async def test_delete_entry_commit(client):
    out = await entries.run_delete(
        client,
        SID,
        DeleteEntryInput(org_id=ORG, address_book_id=AB, entry_id="e3", confirm=True),
    )
    assert out.committed is True


async def test_bulk_save_dry_run_then_commit(client):
    payload = BulkSaveEntriesInput(
        org_id=ORG,
        address_book_id=AB,
        entries=[
            EntryInput(name="A", number="+14155550001"),
            EntryInput(name="B", number="+14155550002"),
        ],
    )
    preview = await entries.run_bulk_save(client, SID, payload)
    assert preview.dry_run is True
    assert preview.preview["entry_count"] == 2

    payload.confirm = True
    out = await entries.run_bulk_save(client, SID, payload)
    assert out.committed is True
