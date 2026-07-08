"""Pytest fixtures with mocked WxCC API responses.

Tests never hit live APIs: an ``httpx.MockTransport`` serves canned JSON, and a
fake token broker returns a placeholder token (never a real credential).
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


# A dataset that produces an all-pass routing validation.
DEFAULT_DATASET: dict[str, Any] = {
    "user": {
        "id": "u1",
        "email": "agent@example.com",
        "displayName": "Agent One",
        "active": True,
        "licenses": [{"id": "lic1", "name": "CC Premium"}],
        "lastModified": "2026-07-01T10:00:00Z",
        "teams": [{"id": "t1", "name": "Team Alpha"}],
        "skillProfile": {
            "id": "sp1",
            "name": "Sales",
            "skills": [{"name": "English", "type": "boolean", "values": ["true"]}],
        },
        "agentProfile": "Default Agent Profile",
        "multimediaProfile": {
            "id": "mm1",
            "name": "Standard",
            "channelsEnabled": ["telephony"],
        },
    },
    "teams": {
        "t1": {
            "name": "Team Alpha",
            "site": "Site 1",
            "members": [{"id": "u1", "name": "Agent One"}],
            "queues": [{"id": "q1", "name": "Sales Queue"}],
        }
    },
    "queues": {
        "q1": {
            "name": "Sales Queue",
            "active": True,
            "channelType": "telephony",
            "requiredSkills": [{"name": "English", "type": "boolean", "values": ["true"]}],
            "routingType": "LONGEST_AVAILABLE",
        }
    },
    "skill_profiles": {
        "sp1": {
            "name": "Sales",
            "skills": [{"name": "English", "type": "boolean", "values": ["true"]}],
        }
    },
    "state_history": {
        "items": [
            {
                "fromState": "Idle",
                "toState": "Available",
                "reasonCode": None,
                "timestamp": "2026-07-01T09:00:00Z",
            }
        ]
    },
    "session": {
        "items": [
            {
                "active": True,
                "loginTimestamp": "2026-07-01T08:00:00Z",
                "deviceType": "desktop",
                "channels": ["telephony"],
            }
        ]
    },
}


def _last_segment(path: str) -> str:
    return path.rstrip("/").rsplit("/", 1)[-1]


def make_handler(
    dataset: dict[str, Any] | None = None,
    errors: dict[str, int] | None = None,
) -> Callable[[httpx.Request], httpx.Response]:
    """Build a MockTransport handler over a dataset, with optional error injection.

    Args:
        dataset: Canned data (defaults to :data:`DEFAULT_DATASET`).
        errors: Map of category -> HTTP status to force, where category is one of
            ``user``, ``team``, ``queue``, ``skill_profile``, ``state``, ``session``.
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

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/agent-state/search"):
            return _err_or("state", data.get("state_history"))
        if path.endswith("/agent-session/search"):
            return _err_or("session", data.get("session"))
        if "/contact-service-queue/" in path:
            return _err_or("queue", data.get("queues", {}).get(_last_segment(path)))
        if "/team/" in path:
            return _err_or("team", data.get("teams", {}).get(_last_segment(path)))
        if "/skill-profile/" in path:
            return _err_or("skill_profile", data.get("skill_profiles", {}).get(_last_segment(path)))
        if path.endswith("/user"):
            # Search by email -> list wrapper.
            return _err_or("user", {"items": [data["user"]]} if data.get("user") else None)
        if "/user/" in path:
            return _err_or("user", data.get("user"))
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
    """Return an all-pass mocked client, closing it after the test."""
    c, _ = build_client(make_handler(), broker)
    yield c
    await c.aclose()


@pytest.fixture
def client_factory():
    """Return a factory to build clients with custom dataset/errors.

    Usage:
        client = client_factory(dataset=..., errors={"state": 403})
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
