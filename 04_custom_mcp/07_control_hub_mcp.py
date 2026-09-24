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
log = logging.getLogger("control-hub-mcp")

load_dotenv()
TOKEN = os.environ.get("ACCESS_TOKEN")

if not TOKEN:
    sys.exit("ACCESS_TOKEN is not set. Please set it in your .env file.")

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

mcp = MCPServer("webex-control-hub-mcp")

@mcp.tool()
async def list_people(max_results: int = 10) -> dict:
    """List users (people) in the organization."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://webexapis.com/v1/people",
            headers=HEADERS,
            params={"max": max_results}
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    people = r.json().get("items", [])
    return {
        "count": len(people),
        "people": [
            {"id": p.get("id"), "emails": p.get("emails"), "displayName": p.get("displayName")}
            for p in people
        ]
    }

@mcp.tool()
async def list_workspaces(max_results: int = 10) -> dict:
    """List workspaces in the organization."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://webexapis.com/v1/workspaces",
            headers=HEADERS,
            params={"max": max_results}
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    workspaces = r.json().get("items", [])
    return {
        "count": len(workspaces),
        "workspaces": [
            {"id": w.get("id"), "displayName": w.get("displayName"), "type": w.get("type")}
            for w in workspaces
        ]
    }

@mcp.tool()
async def list_licenses() -> dict:
    """List licenses in the organization."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://webexapis.com/v1/licenses",
            headers=HEADERS
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    licenses = r.json().get("items", [])
    return {
        "count": len(licenses),
        "licenses": [
            {"id": l.get("id"), "name": l.get("name"), "consumedUnits": l.get("consumedUnits"), "totalUnits": l.get("totalUnits")}
            for l in licenses
        ]
    }

@mcp.tool()
async def list_roles(max_results: int = 20) -> dict:
    """List admin roles available in the organization."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://webexapis.com/v1/roles",
            headers=HEADERS,
            params={"max": max_results}
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    roles = r.json().get("items", [])
    return {
        "count": len(roles),
        "roles": [
            {"id": role.get("id"), "name": role.get("name"), "description": role.get("description")}
            for role in roles
        ]
    }

if __name__ == "__main__":
    log.info("webex-control-hub-mcp running on stdio - waiting for a client (Ctrl+C to stop).")
    try:
        mcp.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
