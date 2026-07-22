"""Tools: desktop profile reads + the gated assign-address-book-to-profile write.

Assignment sets the profile's ``addressBookId`` while preserving all other
(non-deprecated) profile fields. The deprecated dial-plan fields are never
touched. Response field names are marked ``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from ..api import desktop_profiles as api
from ..api.client import WxccApiClient
from ..logging_config import get_logger
from ..models.schemas import (
    AssignAddressBookInput,
    DesktopProfileItem,
    GetDesktopProfileInput,
    ListDesktopProfilesInput,
    ListDesktopProfilesOutput,
    WriteOutput,
)
from ._helpers import committed_response, dry_run_response, extract_items

logger = get_logger(__name__)

# Deprecated Desktop Profile fields (removed 2026-09-15). Never send these back.
_DEPRECATED_FIELDS = ("dialPlans", "agentDNValidationCriteria", "agentDNValidationCriterions")


def _map_profile(raw: dict[str, Any]) -> DesktopProfileItem:
    """Map a raw desktop profile record to a :class:`DesktopProfileItem`. VERIFY fields."""
    return DesktopProfileItem(
        profile_id=str(raw.get("id") or raw.get("profileId") or ""),  # VERIFY
        name=raw.get("name"),  # VERIFY
        address_book_id=raw.get("addressBookId"),  # VERIFY
    )


async def run_list(
    client: WxccApiClient, session_id: str, inp: ListDesktopProfilesInput
) -> ListDesktopProfilesOutput:
    """List desktop profiles in an organization."""
    logger.info("tool_invoked", tool="list_desktop_profiles", org_id=inp.org_id)
    raw = await api.list_desktop_profiles(
        client, session_id, inp.org_id, max_results=inp.max_results
    )
    profiles = [_map_profile(item) for item in extract_items(raw)]
    return ListDesktopProfilesOutput(
        org_id=inp.org_id, total_returned=len(profiles), profiles=profiles
    )


async def run_get(
    client: WxccApiClient, session_id: str, inp: GetDesktopProfileInput
) -> DesktopProfileItem:
    """Get a single desktop profile by id."""
    logger.info("tool_invoked", tool="get_desktop_profile", profile_id=inp.profile_id)
    raw = await api.get_desktop_profile(client, session_id, inp.org_id, inp.profile_id)
    record = raw if isinstance(raw, dict) else {}
    return _map_profile(record)


async def run_assign_address_book(
    client: WxccApiClient, session_id: str, inp: AssignAddressBookInput
) -> WriteOutput:
    """Assign an address book to a desktop profile (dry-run unless ``confirm`` is set).

    Reads the current profile, changes only ``addressBookId``, strips deprecated
    fields, and writes the object back so other settings are preserved.
    """
    logger.info(
        "tool_invoked",
        tool="assign_address_book_to_profile",
        profile_id=inp.profile_id,
        address_book_id=inp.address_book_id,
        dry_run=not inp.confirm,
    )
    current = await api.get_desktop_profile(client, session_id, inp.org_id, inp.profile_id)
    current_dict = current if isinstance(current, dict) else {}
    preview = {
        "action": "assign_address_book_to_profile",
        "profile_id": inp.profile_id,
        "current_address_book_id": current_dict.get("addressBookId"),  # VERIFY
        "proposed_address_book_id": inp.address_book_id,
    }
    if not inp.confirm:
        return WriteOutput(**dry_run_response(preview))

    payload = {k: v for k, v in current_dict.items() if k not in _DEPRECATED_FIELDS}
    payload["addressBookId"] = inp.address_book_id  # VERIFY
    result = await api.update_desktop_profile(
        client, session_id, inp.org_id, inp.profile_id, payload
    )
    return WriteOutput(**committed_response(result, inp.profile_id))
