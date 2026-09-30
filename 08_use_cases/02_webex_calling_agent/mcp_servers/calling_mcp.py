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
    params = {"orgId": ORG_ID} if ORG_ID else {}
    params["email" if "@" in person else "displayName"] = person
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

async def confirm_outgoing_permission(person_id: str, call_type: str, action: str) -> Elicit[Confirm]:
    who = await _person_label(person_id)
    verb = "Block" if action.upper() == "BLOCK" else "Allow"
    return Elicit(f"{verb} outgoing '{call_type}' calls for {who}?", Confirm)

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
async def get_outgoing_permission(person_id: str) -> dict:
    """Show a user's outgoing calling permissions — which categories of calls
    (call types) the user is allowed to dial or is blocked from dialing. Identify
    the user by their email address, their display name (e.g. 'Pod 0'), or their
    Webex personId. Call types include TOLL_FREE (1-800 numbers), NATIONAL,
    INTERNATIONAL, and others; each has an action of ALLOW or BLOCK. If a user
    reports that a call to a number failed and their license, number, and device
    are healthy, read this to see whether that number's call type is blocked.
    Same setting an admin sees in Control Hub under the user's
    Calling > Permissions > Outgoing calls."""
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

@mcp.tool()
async def update_outgoing_permission(
    person_id: str,
    call_type: str = "TOLL_FREE",
    action: str = "BLOCK",
    confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_outgoing_permission)] = None,
) -> dict:
    """Allow or block a category of outgoing calls for a user. Identify the user
    by their email address, their display name (e.g. 'Pod 0'), or their Webex
    personId. Set `action` to BLOCK to stop the user dialing that `call_type`, or
    ALLOW to permit it again. `call_type` is a Webex call category such as
    TOLL_FREE (1-800 numbers), NATIONAL, or INTERNATIONAL. Blocking TOLL_FREE,
    for example, makes calls to 1-800 numbers fail for that user until you set it
    back to ALLOW. The server asks you to confirm first. Same setting an admin
    sees in Control Hub under the user's Calling > Permissions > Outgoing calls."""
    action = action.upper()
    match confirm:
        case AcceptedElicitation(data=Confirm(ok=True)):
            pid = await _resolve_person_id(person_id)
            if not pid:
                return {"error": f"Could not find a user matching '{person_id}'."}
            params = {"orgId": ORG_ID} if ORG_ID else {}
            url = f"https://webexapis.com/v1/people/{pid}/features/outgoingPermission"
            async with httpx.AsyncClient(timeout=15) as http:
                current = await http.get(url, headers=HEADERS, params=params)
                if current.status_code != 200:
                    return {"error": f"HTTP {current.status_code}: {current.text}"}
                permissions = current.json().get("callingPermissions", [])
                found = False
                for perm in permissions:
                    if perm.get("callType") == call_type:
                        perm["action"] = action
                        found = True
                if not found:
                    return {"error": f"Unknown call type '{call_type}'."}
                payload = {"useCustomEnabled": True, "callingPermissions": permissions}
                r = await http.put(url, headers=HEADERS, params=params, json=payload)
            if r.status_code not in (200, 204):
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            return {"updated": True, "person_id": person_id,
                    "call_type": call_type, "action": action}
        case AcceptedElicitation():
            return {"updated": False, "reason": "You chose not to change outgoing permissions."}
        case DeclinedElicitation() | CancelledElicitation():
            return {"updated": False, "reason": "Confirmation was declined or dismissed."}

if __name__ == "__main__":
    log.info("webex-calling-complex running on stdio - waiting for a client (Ctrl+C to stop).")
    try:
        mcp.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
