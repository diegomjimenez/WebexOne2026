"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
import logging
import os
import sys
import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("calling-mcp")

load_dotenv()
TOKEN = os.environ.get("ACCESS_TOKEN")

if not TOKEN:
    sys.exit("ACCESS_TOKEN is not set. Please set it in your .env file.")

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

mcp = MCPServer("webex-calling-mcp")

@mcp.tool()
async def list_numbers(max_results: int = 25) -> dict:
    """List phone numbers configured in the organization."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://webexapis.com/v1/telephony/config/numbers",
            headers=HEADERS,
            params={"max": max_results}
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    numbers = r.json().get("phoneNumbers", [])
    return {
        "count": len(numbers),
        "numbers": [
            {"number": n.get("phoneNumber"), "state": n.get("state"), "location": n.get("location", {}).get("name")}
            for n in numbers
        ]
    }

@mcp.tool()
async def list_locations(max_results: int = 10) -> dict:
    """List locations in the organization."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://webexapis.com/v1/locations",
            headers=HEADERS,
            params={"max": max_results}
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    locations = r.json().get("items", [])
    return {
        "count": len(locations),
        "locations": [
            {"id": l.get("id"), "name": l.get("name"), "address": l.get("address", {}).get("city")}
            for l in locations
        ]
    }

@mcp.tool()
async def list_devices(max_results: int = 10) -> dict:
    """List devices in the organization."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://webexapis.com/v1/devices",
            headers=HEADERS,
            params={"max": max_results}
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    devices = r.json().get("items", [])
    return {
        "count": len(devices),
        "devices": [
            {"id": d.get("id"), "product": d.get("product"), "type": d.get("type"), "connectionStatus": d.get("connectionStatus")}
            for d in devices
        ]
    }

@mcp.tool()
async def get_location_call_settings(location_id: str) -> dict:
    """Manage specific calling settings for a location."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            f"https://webexapis.com/v1/telephony/config/locations/{location_id}",
            headers=HEADERS
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    return r.json()

if __name__ == "__main__":
    log.info("webex-calling-mcp running on stdio - waiting for a client (Ctrl+C to stop).")
    try:
        mcp.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
