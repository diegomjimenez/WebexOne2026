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

async def confirm_delete_device(device_id: str) -> Elicit[Confirm]:
    return Elicit(f"Delete device '{device_id}'? This cannot be undone.", Confirm)

async def confirm_call_forwarding(person_id: str, forward_all_to: str) -> Elicit[Confirm]:
    if forward_all_to:
        msg = f"Forward all calls for user '{person_id}' to {forward_all_to}?"
    else:
        msg = f"Turn off 'forward all calls' for user '{person_id}'?"
    return Elicit(msg, Confirm)

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
        r = await http.get("https://webexapis.com/v1/telephony/config/dialPlans", headers=HEADERS)
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
    """Show a user's call forwarding settings. This is the same setting the
    user sees in their Webex app under Settings > Calling > Call forwarding."""
    params = {"orgId": ORG_ID} if ORG_ID else {}
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            f"https://webexapis.com/v1/people/{person_id}/features/callForwarding",
            headers=HEADERS, params=params
        )
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def update_call_forwarding(
    person_id: str,
    forward_all_to: str = "",
    confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_call_forwarding)] = None,
) -> dict:
    """Set or clear 'forward all calls' for a user. Pass forward_all_to as the
    destination number to enable it, or leave it empty to turn forwarding off.
    The server asks you to confirm first. This is the same setting the user
    sees in their Webex app under Settings > Calling > Call forwarding."""
    match confirm:
        case AcceptedElicitation(data=Confirm(ok=True)):
            params = {"orgId": ORG_ID} if ORG_ID else {}
            url = f"https://webexapis.com/v1/people/{person_id}/features/callForwarding"
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

if __name__ == "__main__":
    log.info("webex-calling-complex running on stdio - waiting for a client (Ctrl+C to stop).")
    try:
        mcp.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
