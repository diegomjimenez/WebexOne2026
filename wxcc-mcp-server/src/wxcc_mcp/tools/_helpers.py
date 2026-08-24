"""Shared helpers for all tool modules."""

from __future__ import annotations

from typing import Any


def extract_items(raw: Any, *keys: str) -> list[dict[str, Any]]:
    """Pull a list of records from an API response regardless of envelope shape."""
    if isinstance(raw, list):
        return [i for i in raw if isinstance(i, dict)]
    if isinstance(raw, dict):
        for key in keys or ("items", "data"):
            val = raw.get(key)
            if isinstance(val, list):
                return [i for i in val if isinstance(i, dict)]
        # Try all dict values
        for val in raw.values():
            if isinstance(val, list) and val and isinstance(val[0], dict):
                return [i for i in val if isinstance(i, dict)]
    return []


def dry_run_response(preview: dict[str, Any]) -> dict[str, Any]:
    """Build the shared "did not commit" result.

    The message is deliberately neutral. Advice on how to proceed depends on
    *why* the write was blocked — telling a caller to pass ``confirm`` is correct
    when nobody could be asked and an invitation to retry past a human when
    somebody refused — so it is supplied centrally from the gate's decision
    rather than hardcoded here.
    """
    return {
        "dry_run": True,
        "committed": False,
        "preview": preview,
        "message": "Not committed.",
    }


def committed_response(result: Any, resource_id: str | None = None) -> dict[str, Any]:
    return {
        "dry_run": False,
        "committed": True,
        "resource_id": resource_id,
        "result": result,
        "message": "Change committed successfully.",
    }
