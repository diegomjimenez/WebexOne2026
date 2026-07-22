"""Tests for desktop profile / agent reads, the mapping, and address-book assignment."""

from __future__ import annotations

import json

import httpx

from wxcc_mcp.api.client import WxccApiClient
from wxcc_mcp.models.schemas import (
    AssignAddressBookInput,
    GetDesktopProfileInput,
    ListAgentsInput,
    ListDesktopProfilesInput,
    ProfileAgentMapInput,
)
from wxcc_mcp.tools import agents, desktop_profiles

from .conftest import FakeBroker

ORG = "org1"
SID = "s1"


async def test_list_desktop_profiles(client):
    out = await desktop_profiles.run_list(client, SID, ListDesktopProfilesInput(org_id=ORG))
    assert out.total_returned == 2
    p2 = next(p for p in out.profiles if p.profile_id == "p2")
    assert p2.address_book_id == "ab2"


async def test_get_desktop_profile(client):
    out = await desktop_profiles.run_get(
        client, SID, GetDesktopProfileInput(org_id=ORG, profile_id="p1")
    )
    assert out.profile_id == "p1"
    assert out.address_book_id is None


async def test_list_agents(client):
    out = await agents.run_list(client, SID, ListAgentsInput(org_id=ORG))
    assert out.total_returned == 4


async def test_map_profiles_to_agents(client):
    out = await agents.run_map_profiles_to_agents(client, SID, ProfileAgentMapInput(org_id=ORG))
    by_profile = {m.profile_id: m for m in out.mappings}
    assert {a.user_id for a in by_profile["p1"].agents} == {"a1", "a2"}
    assert {a.user_id for a in by_profile["p2"].agents} == {"a3"}
    assert {a.user_id for a in out.unassigned_agents} == {"a4"}


async def test_assign_address_book_dry_run(client):
    preview = await desktop_profiles.run_assign_address_book(
        client, SID, AssignAddressBookInput(org_id=ORG, profile_id="p1", address_book_id="ab1")
    )
    assert preview.dry_run is True
    assert preview.preview["proposed_address_book_id"] == "ab1"
    assert preview.preview["current_address_book_id"] is None


async def test_assign_address_book_preserves_fields_and_strips_deprecated():
    """The PUT payload must keep non-deprecated fields, set addressBookId, and drop
    the deprecated dial-plan fields."""
    captured: dict[str, object] = {}

    profile = {
        "id": "p1",
        "name": "Sales Desktop",
        "addressBookId": None,
        "screenPopEnabled": True,  # a non-deprecated field to preserve
        "dialPlans": ["should-be-removed"],  # deprecated
        "agentDNValidationCriteria": "US",  # deprecated
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PUT":
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(200, json={"id": "p1"})
        return httpx.Response(200, json=profile)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api_client = WxccApiClient(FakeBroker(), http_client=http)  # type: ignore[arg-type]
    try:
        out = await desktop_profiles.run_assign_address_book(
            api_client,
            SID,
            AssignAddressBookInput(
                org_id=ORG, profile_id="p1", address_book_id="ab1", confirm=True
            ),
        )
    finally:
        await api_client.aclose()

    assert out.committed is True
    assert captured["addressBookId"] == "ab1"
    assert captured["screenPopEnabled"] is True
    assert captured["name"] == "Sales Desktop"
    assert "dialPlans" not in captured
    assert "agentDNValidationCriteria" not in captured
