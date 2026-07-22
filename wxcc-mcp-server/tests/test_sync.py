"""Tests for the composite CRM→address-book sync diff and apply flow."""

from __future__ import annotations

from wxcc_mcp.models.schemas import CrmContact, EntryItem, SyncCrmInput
from wxcc_mcp.resources import crm_contacts
from wxcc_mcp.tools import sync

ORG = "org1"
SID = "s1"
AB = "ab1"


def _existing() -> list[EntryItem]:
    return [
        EntryItem(
            entry_id="e1", name="Acme Corp — Reception", number="+14155550101", crm_id="crm-1001"
        ),
        EntryItem(
            entry_id="e2",
            name="Acme Corp — Billing (OLD)",
            number="+14155550102",
            crm_id="crm-1002",
        ),
        EntryItem(entry_id="e3", name="Stale Contact", number="+19998887777"),
    ]


def test_compute_diff_prune_off():
    contacts = [CrmContact(**c) for c in crm_contacts.get_contacts()]
    actions = sync.compute_diff(contacts, _existing(), prune=False)
    kinds = [a.action for a in actions]
    assert kinds.count("create") == 5
    assert kinds.count("update") == 1
    assert kinds.count("delete") == 0
    # e1 unchanged + e3 absent (not pruned) => 2 skips
    assert kinds.count("skip") == 2


def test_compute_diff_prune_on():
    contacts = [CrmContact(**c) for c in crm_contacts.get_contacts()]
    actions = sync.compute_diff(contacts, _existing(), prune=True)
    kinds = [a.action for a in actions]
    assert kinds.count("create") == 5
    assert kinds.count("update") == 1
    assert kinds.count("delete") == 1
    assert kinds.count("skip") == 1


def test_compute_diff_matches_by_number_without_crm_id():
    contacts = [CrmContact(id="crm-x", name="Renamed", number="+14155550101")]
    existing = [EntryItem(entry_id="e1", name="Old Name", number="+14155550101")]
    actions = sync.compute_diff(contacts, existing, prune=False)
    assert len(actions) == 1
    assert actions[0].action == "update"
    assert actions[0].entry_id == "e1"


async def test_sync_dry_run(client):
    out = await sync.run(client, SID, SyncCrmInput(org_id=ORG, address_book_id=AB))
    assert out.dry_run is True
    assert out.committed is False
    assert out.to_create == 5
    assert out.to_update == 1
    assert out.to_delete == 0
    assert out.message


async def test_sync_commit_applies_changes_with_progress(client):
    progress_calls: list[tuple[float, float]] = []

    async def on_progress(done: float, total: float, message: str) -> None:
        progress_calls.append((done, total))

    out = await sync.run(
        client,
        SID,
        SyncCrmInput(org_id=ORG, address_book_id=AB, confirm=True),
        on_progress=on_progress,
    )
    assert out.committed is True
    assert out.to_create == 5
    assert out.to_update == 1
    # 5 creates + 1 update = 6 applied changes; progress fires once per change.
    assert len(progress_calls) == 6
    assert progress_calls[-1][0] == progress_calls[-1][1]


async def test_sync_commit_with_prune_deletes(client):
    out = await sync.run(
        client, SID, SyncCrmInput(org_id=ORG, address_book_id=AB, prune=True, confirm=True)
    )
    assert out.committed is True
    assert out.to_delete == 1
