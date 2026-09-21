"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
import logging
import os
import sys
import httpx
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from mcp.server import MCPServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("troubleshooting-mcp")

load_dotenv()
TOKEN = os.environ.get("ACCESS_TOKEN")
ORG_ID = os.environ.get("WEBEX_ORG_ID")

if not TOKEN or not ORG_ID:
    sys.exit("ACCESS_TOKEN and WEBEX_ORG_ID must be set in your .env file.")

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

mcp = MCPServer("webex-troubleshooting-mcp")

@mcp.tool()
async def unresolved_incidents() -> dict:
    """Check Webex for any unresolved platform incidents."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get("https://status.webex.com/unresolved-incidents.json")
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    incidents = r.json().get("incidents", [])
    return {"count": len(incidents), "incidents": incidents}

@mcp.tool()
async def list_admin_audit_events(days_back: int = 7, max_results: int = 10) -> dict:
    """List recent admin audit events in the organization."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=days_back)
    
    params = {
        "orgId": ORG_ID,
        "from": past.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "to": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "max": max_results
    }
    
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://webexapis.com/v1/adminAudit/events",
            headers=HEADERS,
            params=params
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    events = r.json().get("items", [])
    return {
        "count": len(events),
        "events": [
            {
                "id": e.get("id"),
                "created": e.get("created"),
                "actionText": e.get("data", {}).get("actionText"),
                "actorEmail": e.get("data", {}).get("actorEmail"),
                "category": e.get("data", {}).get("eventCategory"),
            }
            for e in events
        ]
    }

@mcp.tool()
async def list_reports() -> dict:
    """List recent usage and activity reports generated in the organization."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://webexapis.com/v1/reports",
            headers=HEADERS
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    reports = r.json().get("items", [])
    return {
        "count": len(reports),
        "reports": [
            {"id": rep.get("Id"), "title": rep.get("title"), "status": rep.get("status")}
            for rep in reports
        ]
    }

@mcp.tool()
async def list_ended_meetings(days_back: int = 7, max_results: int = 10) -> dict:
    """List meetings that already ended, so their IDs can be used for quality analysis."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=days_back)

    params = {
        "meetingType": "meeting",
        "state": "ended",
        "from": past.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max": max_results
    }

    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://webexapis.com/v1/meetings",
            headers=HEADERS,
            params=params
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}

    meetings = r.json().get("items", [])
    return {
        "count": len(meetings),
        "meetings": [
            {"id": m.get("id"), "title": m.get("title"), "start": m.get("start"), "end": m.get("end")}
            for m in meetings
        ]
    }

@mcp.tool()
async def get_meeting_qualities(meeting_id: str) -> dict:
    """Analytics and diagnostics for an ended meeting. Use the ID from list_ended_meetings."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://analytics.webexapis.com/v1/meeting/qualities",
            headers=HEADERS,
            params={"meetingId": meeting_id}
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    return r.json()

if __name__ == "__main__":
    log.info("webex-troubleshooting-mcp running on stdio - waiting for a client (Ctrl+C to stop).")
    try:
        mcp.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
