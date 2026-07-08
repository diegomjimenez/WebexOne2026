"""Tests for the OAuth token broker: per-session isolation and refresh."""

from __future__ import annotations

import time

import pytest

from wxcc_mcp.auth.oauth import EncryptedTokenStore, OAuthBroker, TokenSet
from wxcc_mcp.config import Settings
from wxcc_mcp.errors import AuthError


def _settings(tmp_path) -> Settings:
    return Settings(
        token_store_dir=str(tmp_path / "tokens"),
        token_encryption_key="",  # ephemeral key path
    )


def test_sessions_are_isolated(tmp_path):
    store = EncryptedTokenStore(key="", store_dir=str(tmp_path / "tokens"))
    store.save("session-a", TokenSet(access_token="token-a", expires_at=time.time() + 3600))
    store.save("session-b", TokenSet(access_token="token-b", expires_at=time.time() + 3600))

    a = store.load("session-a")
    b = store.load("session-b")
    assert a is not None and a.access_token == "token-a"
    assert b is not None and b.access_token == "token-b"
    # Session A must never see session B's token.
    assert a.access_token != b.access_token


def test_tokens_are_encrypted_at_rest(tmp_path):
    store_dir = tmp_path / "tokens"
    store = EncryptedTokenStore(key="", store_dir=str(store_dir))
    store.save("session-a", TokenSet(access_token="super-secret-token"))

    # The raw file on disk must not contain the plaintext token.
    files = list(store_dir.glob("*.token"))
    assert files, "expected an encrypted token file"
    raw = files[0].read_bytes()
    assert b"super-secret-token" not in raw


async def test_get_valid_token_requires_authorization(tmp_path):
    broker = OAuthBroker(settings=_settings(tmp_path))
    with pytest.raises(AuthError):
        await broker.get_valid_token("never-authorized")


async def test_expired_token_without_refresh_raises(tmp_path):
    broker = OAuthBroker(settings=_settings(tmp_path))
    # Store an already-expired token with no refresh token.
    broker._store.save(  # noqa: SLF001 - exercising internal store deliberately
        "s1", TokenSet(access_token="expired", refresh_token=None, expires_at=0.0)
    )
    with pytest.raises(AuthError):
        await broker.get_valid_token("s1")
