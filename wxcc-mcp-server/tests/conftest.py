"""Pytest fixtures with mocked WxCC Config API responses.

Tests never hit live APIs: an ``httpx.MockTransport`` serves canned JSON, and a
fake token broker returns a placeholder token (never a real credential). The
mocked handler covers the address book, entry, desktop profile, and user
endpoints used by the address-book sync scenario.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from wxcc_mcp.api.client import WxccApiClient


class FakeBroker:
    """A stand-in OAuth broker that returns a fixed, fake token."""

    def __init__(self, token: str = "fake-access-token") -> None:
        self.token = token
        self.sessions_seen: list[str] = []

    async def get_valid_token(self, session_id: str) -> str:
        """Return the fake token, recording the session id used."""
        self.sessions_seen.append(session_id)
        return self.token


# A dataset aligned to the CRM fixture (crm-1001..crm-1007) so sync tests have a
# deterministic diff: e1 unchanged, e2 name changed, e3 absent from CRM.
DEFAULT_DATASET: dict[str, Any] = {
    "address_books": {
        "ab1": {
            "id": "ab1",
            "name": "CRM — Enterprise Accounts",
            "description": "Synced from CRM",
            "parentType": "CUSTOMER",
        },
        "ab2": {"id": "ab2", "name": "Site Book", "parentType": "SITE"},
    },
    "entries": {
        "ab1": {
            "e1": {
                "id": "e1",
                "name": "Acme Corp — Reception",
                "number": "+14155550101",
                "crmId": "crm-1001",
            },
            "e2": {
                "id": "e2",
                "name": "Acme Corp — Billing (OLD)",
                "number": "+14155550102",
                "crmId": "crm-1002",
            },
            "e3": {
                "id": "e3",
                "name": "Stale Contact",
                "number": "+19998887777",
            },
        }
    },
    "profiles": {
        "p1": {"id": "p1", "name": "Sales Desktop", "addressBookId": None},
        "p2": {"id": "p2", "name": "Support Desktop", "addressBookId": "ab2"},
    },
    "agents": [
        {"id": "a1", "email": "a1@example.com", "displayName": "Agent One", "agentProfileId": "p1"},
        {"id": "a2", "email": "a2@example.com", "displayName": "Agent Two", "agentProfileId": "p1"},
        {
            "id": "a3",
            "email": "a3@example.com",
            "displayName": "Agent Three",
            "agentProfileId": "p2",
        },
        {
            "id": "a4",
            "email": "a4@example.com",
            "displayName": "Agent Four",
            "agentProfileId": None,
        },
    ],
}


def make_handler(
    dataset: dict[str, Any] | None = None,
    errors: dict[str, int] | None = None,
) -> Callable[[httpx.Request], httpx.Response]:
    """Build a MockTransport handler over a dataset, with optional error injection.

    Args:
        dataset: Canned data (defaults to :data:`DEFAULT_DATASET`).
        errors: Map of category -> HTTP status to force, where category is one of
            ``address_book``, ``entry``, ``profile``, ``user``.
    """
    data = copy.deepcopy(dataset if dataset is not None else DEFAULT_DATASET)
    errors = errors or {}

    def _err_or(category: str, body: Any) -> httpx.Response:
        status = errors.get(category)
        if status:
            return httpx.Response(status, json={"message": f"forced {status} for {category}"})
        if body is None:
            return httpx.Response(404, json={"message": "not found"})
        return httpx.Response(200, json=body)

    def _address_book(parts: list[str], method: str) -> httpx.Response:
        # parts: [organization, {org}, address-book, {ab_id?}, entry?, {eid|bulk}?]
        books = data.get("address_books", {})
        if len(parts) == 3:  # /address-book
            if method == "POST":
                return _err_or("address_book", {"id": "ab-new"})
            return _err_or("address_book", list(books.values()))
        ab_id = parts[3]
        if len(parts) == 4:  # /address-book/{ab_id}
            if method == "DELETE":
                return _err_or("address_book", {})
            if method == "PUT":
                return _err_or("address_book", {"id": ab_id})
            return _err_or("address_book", books.get(ab_id))
        if len(parts) >= 5 and parts[4] == "entry":
            entries = data.get("entries", {}).get(ab_id, {})
            if len(parts) == 5:  # /entry
                if method == "POST":
                    return _err_or("entry", {"id": "e-new"})
                return _err_or("entry", list(entries.values()))
            tail = parts[5]
            if tail == "bulk":  # /entry/bulk
                return _err_or("entry", {"saved": True})
            if method == "DELETE":
                return _err_or("entry", {})
            if method == "PUT":
                return _err_or("entry", {"id": tail})
            return _err_or("entry", entries.get(tail))
        return httpx.Response(404, json={"message": "unmapped address-book path"})

    def _profile(parts: list[str], method: str) -> httpx.Response:
        profiles = data.get("profiles", {})
        if len(parts) == 3:  # /agent-profile
            return _err_or("profile", list(profiles.values()))
        pid = parts[3]
        if method == "PUT":
            # Echo back the request body so field-preservation can be asserted.
            return _err_or("profile", {"id": pid})
        return _err_or("profile", profiles.get(pid))

    def _user(parts: list[str], method: str) -> httpx.Response:
        agents = data.get("agents", [])
        if len(parts) == 3:  # /user
            return _err_or("user", agents)
        uid = parts[3]
        match = next((a for a in agents if a.get("id") == uid), None)
        return _err_or("user", match)

    def handler(request: httpx.Request) -> httpx.Response:
        parts = [p for p in request.url.path.split("/") if p]
        method = request.method
        if len(parts) < 3 or parts[0] != "organization":
            return httpx.Response(404, json={"message": "unmapped path"})
        resource = parts[2]
        if resource == "address-book":
            return _address_book(parts, method)
        if resource == "agent-profile":
            return _profile(parts, method)
        if resource == "user":
            return _user(parts, method)
        return httpx.Response(404, json={"message": "unmapped path"})

    return handler


def build_client(
    handler: Callable[[httpx.Request], httpx.Response],
    broker: FakeBroker | None = None,
) -> tuple[WxccApiClient, FakeBroker]:
    """Construct a WxccApiClient wired to a MockTransport handler."""
    broker = broker or FakeBroker()
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = WxccApiClient(broker, http_client=http)  # type: ignore[arg-type]
    return client, broker


@pytest.fixture
def broker() -> FakeBroker:
    """Return a fresh fake broker."""
    return FakeBroker()


@pytest.fixture
async def client(broker: FakeBroker):
    """Return a mocked client over the default dataset, closing it after the test."""
    c, _ = build_client(make_handler(), broker)
    yield c
    await c.aclose()


@pytest.fixture
def client_factory():
    """Return a factory to build clients with custom dataset/errors.

    Usage:
        client = client_factory(dataset=..., errors={"entry": 403})
    """
    created: list[WxccApiClient] = []

    def _factory(
        dataset: dict[str, Any] | None = None,
        errors: dict[str, int] | None = None,
    ) -> WxccApiClient:
        c, _ = build_client(make_handler(dataset, errors))
        created.append(c)
        return c

    return _factory
