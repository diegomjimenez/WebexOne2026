"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
import logging
import os
import sys
from typing import Annotated
import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer
from mcp.server.mcpserver import (
    AcceptedElicitation, CancelledElicitation, DeclinedElicitation,
    Elicit, ElicitationResult, Resolve
)
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("calling-mcp-complex")

load_dotenv()
TOKEN = os.environ.get("ACCESS_TOKEN")
ORG_ID = os.environ.get("WEBEX_ORG_ID")

if not TOKEN:
    sys.exit("ACCESS_TOKEN is not set. Please set it in your .env file.")

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
mcp = MCPServer("webex-calling-complex")

class Confirm(BaseModel):
    ok: bool

# A Webex Hydra personId is base64 of "ciscospark://..."; it always starts with
# this prefix. Anything else we receive is an email or a display name to resolve.
_PERSON_ID_PREFIX = "Y2lzY29zcGFyazov"

async def _resolve_person_id(person: str) -> str:
    """Accept an email address, a display name (e.g. 'Pod 0'), or a Webex
    personId, and return a personId. Emails and names are resolved through the
    People API; a personId is returned as-is. Returns '' when nothing matches."""
    if not person:
        return ""
    if person.startswith(_PERSON_ID_PREFIX):
        return person  # already a personId
    # The People API rejects a raw-UUID orgId (it wants the base64 Hydra id) and
    # the token is already scoped to one org, so we omit orgId here.
    params = {"email" if "@" in person else "displayName": person}
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            r = await http.get("https://webexapis.com/v1/people", headers=HEADERS, params=params)
        if r.status_code == 200:
            items = r.json().get("items", [])
            if items:
                return items[0].get("id", "")
    except Exception:
        pass
    return ""

async def _person_label(person: str) -> str:
    """Human-readable label for a personId, email, or display name, so
    confirmation cards never show a raw base64 ID. Falls back to a neutral
    phrase rather than leaking an unresolved identifier."""
    if not person:
        return "the requested user"
    if not person.startswith(_PERSON_ID_PREFIX):
        return person  # an email or display name is already human-readable
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            r = await http.get(f"https://webexapis.com/v1/people/{person}", headers=HEADERS)
        if r.status_code == 200:
            data = r.json()
            emails = data.get("emails") or []
            return data.get("displayName") or (emails[0] if emails else "the requested user")
    except Exception:
        pass
    return "the requested user"

async def confirm_delete_device(device_id: str) -> Elicit[Confirm]:
    return Elicit(f"Delete device '{device_id}'? This cannot be undone.", Confirm)

async def confirm_call_forwarding(person_id: str, forward_all_to: str) -> Elicit[Confirm]:
    who = await _person_label(person_id)
    if forward_all_to:
        msg = f"Forward all calls for {who} to {forward_all_to}?"
    else:
        msg = f"Turn off 'forward all calls' for {who}?"
    return Elicit(msg, Confirm)

def _digits(number: str) -> str:
    """Reduce a phone number to just its dialable digits, e.g.
    '1-800-444-4444' -> '18004444444'."""
    return "".join(ch for ch in (number or "") if ch.isdigit())

async def confirm_block_number(person_id: str, number: str) -> Elicit[Confirm]:
    who = await _person_label(person_id)
    return Elicit(f"Block calls to {number} for {who}?", Confirm)

async def confirm_unblock_number(person_id: str, number: str) -> Elicit[Confirm]:
    who = await _person_label(person_id)
    return Elicit(f"Unblock calls to {number} for {who}?", Confirm)

async def confirm_block_toll_free(person_id: str) -> Elicit[Confirm]:
    who = await _person_label(person_id)
    return Elicit(f"Block all toll-free (1-800/888/…) calls for {who}?", Confirm)

async def confirm_unblock_toll_free(person_id: str) -> Elicit[Confirm]:
    who = await _person_label(person_id)
    return Elicit(f"Allow toll-free (1-800/888/…) calls for {who} again?", Confirm)

@mcp.tool()
async def list_numbers(max_results: int = 25) -> dict:
    """List phone numbers configured in the organization."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get("https://webexapis.com/v1/telephony/config/numbers", headers=HEADERS, params={"max": max_results})
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def list_locations(max_results: int = 25) -> dict:
    """List locations in the organization."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get("https://webexapis.com/v1/locations", headers=HEADERS, params={"max": max_results})
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def get_location_call_settings(location_id: str) -> dict:
    """Manage specific calling settings for a location."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(f"https://webexapis.com/v1/telephony/config/locations/{location_id}", headers=HEADERS)
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def list_devices(max_results: int = 25) -> dict:
    """Phones and room devices registered in the org."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get("https://webexapis.com/v1/devices", headers=HEADERS, params={"max": max_results})
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def list_dial_plans() -> dict:
    """List Call Routing dial plans."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get("https://webexapis.com/v1/telephony/config/premisePstn/dialPlans", headers=HEADERS)
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def create_location(name: str, time_zone: str, preferred_language: str, address_line1: str, city: str, state: str, postal_code: str, country: str) -> dict:
    """Create a new location."""
    payload = {
        "name": name,
        "timeZone": time_zone,
        "preferredLanguage": preferred_language,
        "address": {
            "address1": address_line1,
            "city": city,
            "state": state,
            "postalCode": postal_code,
            "country": country
        }
    }
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.post("https://webexapis.com/v1/locations", headers=HEADERS, json=payload)
    return r.json() if r.status_code in (200, 201) else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def delete_device(device_id: str, confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_delete_device)]) -> dict:
    """Delete a device. The server asks you to confirm first."""
    match confirm:
        case AcceptedElicitation(data=Confirm(ok=True)):
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.delete(f"https://webexapis.com/v1/devices/{device_id}", headers=HEADERS)
            if r.status_code not in (200, 204):
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            return {"deleted": True, "device_id": device_id}
        case AcceptedElicitation():
            return {"deleted": False, "reason": "You chose not to delete."}
        case DeclinedElicitation() | CancelledElicitation():
            return {"deleted": False, "reason": "Confirmation was declined or dismissed."}

@mcp.tool()
async def get_call_forwarding(person_id: str) -> dict:
    """Show a user's call forwarding settings. Identify the user by their email
    address, their display name (e.g. 'Pod 0'), or their Webex personId — pass
    whichever the request gives you and the server resolves it. This is the same
    setting the user sees in their Webex app under Settings > Calling >
    Call forwarding."""
    pid = await _resolve_person_id(person_id)
    if not pid:
        return {"error": f"Could not find a user matching '{person_id}'."}
    params = {"orgId": ORG_ID} if ORG_ID else {}
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            f"https://webexapis.com/v1/people/{pid}/features/callForwarding",
            headers=HEADERS, params=params
        )
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def update_call_forwarding(
    person_id: str,
    forward_all_to: str = "",
    confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_call_forwarding)] = None,
) -> dict:
    """Set or clear 'forward all calls' for a user. Identify the user by their
    email address, their display name (e.g. 'Pod 0'), or their Webex personId.
    Pass forward_all_to as the destination number to enable it, or leave it empty
    to turn forwarding off. The server asks you to confirm first. This is the same
    setting the user sees in their Webex app under Settings > Calling >
    Call forwarding."""
    match confirm:
        case AcceptedElicitation(data=Confirm(ok=True)):
            pid = await _resolve_person_id(person_id)
            if not pid:
                return {"error": f"Could not find a user matching '{person_id}'."}
            params = {"orgId": ORG_ID} if ORG_ID else {}
            url = f"https://webexapis.com/v1/people/{pid}/features/callForwarding"
            async with httpx.AsyncClient(timeout=15) as http:
                current = await http.get(url, headers=HEADERS, params=params)
                if current.status_code != 200:
                    return {"error": f"HTTP {current.status_code}: {current.text}"}
                cf = current.json().get("callForwarding", {})
                cf.setdefault("always", {})
                cf["always"]["enabled"] = bool(forward_all_to)
                cf["always"]["destination"] = forward_all_to
                # systemMaxNumberOfRings is read-only; drop it before writing back.
                cf.get("noAnswer", {}).pop("systemMaxNumberOfRings", None)
                r = await http.put(url, headers=HEADERS, params=params,
                                   json={"callForwarding": cf})
            if r.status_code not in (200, 204):
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            return {"updated": True, "person_id": person_id,
                    "forward_all_to": forward_all_to}
        case AcceptedElicitation():
            return {"updated": False, "reason": "You chose not to change call forwarding."}
        case DeclinedElicitation() | CancelledElicitation():
            return {"updated": False, "reason": "Confirmation was declined or dismissed."}

@mcp.tool()
async def list_blocked_numbers(person_id: str) -> dict:
    """List the specific phone numbers a user is blocked from (or explicitly
    allowed to) dial — their outgoing-permission digit patterns. Identify the
    user by email, display name (e.g. 'Pod 0'), or Webex personId. Each entry has
    a `name`, the `pattern` of digits it matches, and an `action` (BLOCK or
    ALLOW). If a user reports that a call to one specific number failed while
    other calls work, read this to see whether that number is blocked. Same list
    an admin sees in Control Hub under the user's
    Calling > Permissions > Outgoing Calls > Digit Patterns."""
    pid = await _resolve_person_id(person_id)
    if not pid:
        return {"error": f"Could not find a user matching '{person_id}'."}
    params = {"orgId": ORG_ID} if ORG_ID else {}
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            f"https://webexapis.com/v1/telephony/config/people/{pid}/outgoingPermission/digitPatterns",
            headers=HEADERS, params=params
        )
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def block_number(
    person_id: str,
    number: str,
    confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_block_number)] = None,
) -> dict:
    """Block a user from dialing one specific phone number. Identify the user by
    email, display name (e.g. 'Pod 0'), or Webex personId, and pass the `number`
    to block (e.g. '1-800-444-4444'). This turns on the user's custom digit
    patterns and adds a BLOCK pattern for that number, so calls to it fail for
    that user until you unblock it. The server asks you to confirm first."""
    match confirm:
        case AcceptedElicitation(data=Confirm(ok=True)):
            pid = await _resolve_person_id(person_id)
            if not pid:
                return {"error": f"Could not find a user matching '{person_id}'."}
            digits = _digits(number)
            if not digits:
                return {"error": f"'{number}' has no dialable digits."}
            params = {"orgId": ORG_ID} if ORG_ID else {}
            base = f"https://webexapis.com/v1/telephony/config/people/{pid}/outgoingPermission/digitPatterns"
            async with httpx.AsyncClient(timeout=15) as http:
                # Enable custom digit patterns so the block is actually enforced.
                cat = await http.put(base, headers=HEADERS, params=params,
                                     json={"useCustomDigitPatterns": True})
                if cat.status_code not in (200, 204):
                    return {"error": f"HTTP {cat.status_code}: {cat.text}"}
                r = await http.post(base, headers=HEADERS, params=params,
                                    json={"name": f"block-{digits}", "pattern": digits,
                                          "action": "BLOCK", "transferEnabled": False})
            if r.status_code not in (200, 201):
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            return {"blocked": True, "person_id": person_id, "number": digits}
        case AcceptedElicitation():
            return {"blocked": False, "reason": "You chose not to block the number."}
        case DeclinedElicitation() | CancelledElicitation():
            return {"blocked": False, "reason": "Confirmation was declined or dismissed."}

@mcp.tool()
async def unblock_number(
    person_id: str,
    number: str,
    confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_unblock_number)] = None,
) -> dict:
    """Remove a block on a specific phone number for a user (the reverse of
    block_number). Identify the user by email, display name (e.g. 'Pod 0'), or
    Webex personId, and pass the `number` to unblock. This deletes the matching
    BLOCK digit pattern so the user can dial the number again. The server asks
    you to confirm first."""
    match confirm:
        case AcceptedElicitation(data=Confirm(ok=True)):
            pid = await _resolve_person_id(person_id)
            if not pid:
                return {"error": f"Could not find a user matching '{person_id}'."}
            digits = _digits(number)
            params = {"orgId": ORG_ID} if ORG_ID else {}
            base = f"https://webexapis.com/v1/telephony/config/people/{pid}/outgoingPermission/digitPatterns"
            async with httpx.AsyncClient(timeout=15) as http:
                listing = await http.get(base, headers=HEADERS, params=params)
                if listing.status_code != 200:
                    return {"error": f"HTTP {listing.status_code}: {listing.text}"}
                matches = [p for p in listing.json().get("digitPatterns", [])
                           if _digits(p.get("pattern", "")) == digits]
                if not matches:
                    return {"unblocked": False, "reason": f"No block found for {digits}."}
                for p in matches:
                    d = await http.delete(f"{base}/{p['id']}", headers=HEADERS, params=params)
                    if d.status_code not in (200, 204):
                        return {"error": f"HTTP {d.status_code}: {d.text}"}
            return {"unblocked": True, "person_id": person_id, "number": digits}
        case AcceptedElicitation():
            return {"unblocked": False, "reason": "You chose not to unblock the number."}
        case DeclinedElicitation() | CancelledElicitation():
            return {"unblocked": False, "reason": "Confirmation was declined or dismissed."}

@mcp.tool()
async def get_calling_permissions(person_id: str) -> dict:
    """Show a user's outgoing calling permissions by call type — whether each
    call type (TOLL_FREE, NATIONAL, INTERNATIONAL, …) is ALLOW or BLOCK, plus
    whether the user is on custom settings (`useCustomEnabled`/
    `useCustomPermissions`). Identify the user by email, display name (e.g.
    'Pod 0'), or Webex personId. If a user reports a whole category of calls
    failing (e.g. every toll-free number), read this to see if that call type is
    set to BLOCK. Same view as Control Hub > user > Calling > Permissions >
    Outgoing Calls > Permissions by type."""
    pid = await _resolve_person_id(person_id)
    if not pid:
        return {"error": f"Could not find a user matching '{person_id}'."}
    params = {"orgId": ORG_ID} if ORG_ID else {}
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            f"https://webexapis.com/v1/people/{pid}/features/outgoingPermission",
            headers=HEADERS, params=params
        )
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

async def _set_toll_free_action(pid: str, action: str) -> dict:
    """Set the TOLL_FREE call-type permission to ALLOW or BLOCK for a user,
    switching them to custom outgoing permissions so the change takes effect.
    Reads the current permission set, flips only the TOLL_FREE entry, and writes
    it back. Returns the updated result or an error dict."""
    params = {"orgId": ORG_ID} if ORG_ID else {}
    url = f"https://webexapis.com/v1/people/{pid}/features/outgoingPermission"
    async with httpx.AsyncClient(timeout=15) as http:
        current = await http.get(url, headers=HEADERS, params=params)
        if current.status_code != 200:
            return {"error": f"HTTP {current.status_code}: {current.text}"}
        data = current.json()
        perms = data.get("callingPermissions", [])
        found = False
        for entry in perms:
            if entry.get("callType") == "TOLL_FREE":
                entry["action"] = action
                # Enforce the restriction so a BLOCK actually applies.
                entry["isCallTypeRestrictionEnabled"] = (action == "BLOCK")
                found = True
        if not found:
            perms.append({"callType": "TOLL_FREE", "action": action,
                          "transferEnabled": False,
                          "isCallTypeRestrictionEnabled": action == "BLOCK"})
        body = {"useCustomEnabled": True, "useCustomPermissions": True,
                "callingPermissions": perms}
        r = await http.put(url, headers=HEADERS, params=params, json=body)
    if r.status_code not in (200, 204):
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    return {}

@mcp.tool()
async def block_toll_free(
    person_id: str,
    confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_block_toll_free)] = None,
) -> dict:
    """Block a user from dialing ALL toll-free numbers (1-800/888/877/…) by
    setting their TOLL_FREE outgoing call-type permission to BLOCK. Identify the
    user by email, display name (e.g. 'Pod 0'), or Webex personId. This switches
    the user to custom outgoing permissions so the block takes effect. Use this
    for the whole toll-free category; to block a single specific number instead,
    use block_number. The server asks you to confirm first."""
    match confirm:
        case AcceptedElicitation(data=Confirm(ok=True)):
            pid = await _resolve_person_id(person_id)
            if not pid:
                return {"error": f"Could not find a user matching '{person_id}'."}
            err = await _set_toll_free_action(pid, "BLOCK")
            if err:
                return err
            return {"blocked": True, "person_id": person_id, "callType": "TOLL_FREE"}
        case AcceptedElicitation():
            return {"blocked": False, "reason": "You chose not to block toll-free calls."}
        case DeclinedElicitation() | CancelledElicitation():
            return {"blocked": False, "reason": "Confirmation was declined or dismissed."}

@mcp.tool()
async def unblock_toll_free(
    person_id: str,
    confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_unblock_toll_free)] = None,
) -> dict:
    """Allow a user to dial toll-free numbers again (the reverse of
    block_toll_free) by setting their TOLL_FREE outgoing call-type permission
    back to ALLOW. Identify the user by email, display name (e.g. 'Pod 0'), or
    Webex personId. The server asks you to confirm first."""
    match confirm:
        case AcceptedElicitation(data=Confirm(ok=True)):
            pid = await _resolve_person_id(person_id)
            if not pid:
                return {"error": f"Could not find a user matching '{person_id}'."}
            err = await _set_toll_free_action(pid, "ALLOW")
            if err:
                return err
            return {"unblocked": True, "person_id": person_id, "callType": "TOLL_FREE"}
        case AcceptedElicitation():
            return {"unblocked": False, "reason": "You chose not to change toll-free permissions."}
        case DeclinedElicitation() | CancelledElicitation():
            return {"unblocked": False, "reason": "Confirmation was declined or dismissed."}

if __name__ == "__main__":
    log.info("webex-calling-complex running on stdio - waiting for a client (Ctrl+C to stop).")
    try:
        mcp.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
