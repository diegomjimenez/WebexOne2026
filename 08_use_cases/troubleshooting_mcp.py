"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
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
log = logging.getLogger("troubleshooting-mcp-complex")

load_dotenv()
TOKEN = os.environ.get("ACCESS_TOKEN")
ORG_ID = os.environ.get("WEBEX_ORG_ID")

if not TOKEN or not ORG_ID:
    sys.exit("ACCESS_TOKEN and WEBEX_ORG_ID must be set in your .env file.")

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
mcp = MCPServer("webex-troubleshooting-complex")

class Confirm(BaseModel):
    ok: bool

async def confirm_delete_report(report_id: str) -> Elicit[Confirm]:
    return Elicit(f"Delete report '{report_id}'? This cannot be undone.", Confirm)

@mcp.tool()
async def unresolved_incidents() -> dict:
    """Check Webex for any unresolved platform incidents."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get("https://status.webex.com/api/v2/incidents/unresolved.json")
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def list_reports() -> dict:
    """List recent usage and activity reports generated in the organization."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get("https://webexapis.com/v1/reports", headers=HEADERS)
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def get_detailed_call_history(days_back: int = 1, max_results: int = 50) -> dict:
    """Get detailed call history (CDRs) for troubleshooting call quality or routing issues."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=days_back)
    params = {
        "startTime": past.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "endTime": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "max": max_results
    }
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get("https://webexapis.com/v1/reports/details/callHistory", headers=HEADERS, params=params)
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def list_admin_audit_events(days_back: int = 7, max_results: int = 25) -> dict:
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
        r = await http.get("https://webexapis.com/v1/adminAudit/events", headers=HEADERS, params=params)
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def get_meeting_qualities(meeting_id: str) -> dict:
    """Analytics and diagnostics for meetings."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(f"https://webexapis.com/v1/meeting/qualities?meetingId={meeting_id}", headers=HEADERS)
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def create_report(template_id: str, start_date: str, end_date: str) -> dict:
    """Create a new report using a template ID. Dates must be YYYY-MM-DD."""
    payload = {
        "templateId": int(template_id) if template_id.isdigit() else template_id,
        "startDate": start_date,
        "endDate": end_date
    }
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.post("https://webexapis.com/v1/reports", headers=HEADERS, json=payload)
    return r.json() if r.status_code in (200, 201) else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def delete_report(report_id: str, confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_delete_report)]) -> dict:
    """Delete a report. The server asks you to confirm first."""
    match confirm:
        case AcceptedElicitation(data=Confirm(ok=True)):
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.delete(f"https://webexapis.com/v1/reports/{report_id}", headers=HEADERS)
            if r.status_code not in (200, 204):
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            return {"deleted": True, "report_id": report_id}
        case AcceptedElicitation():
            return {"deleted": False, "reason": "You chose not to delete."}
        case DeclinedElicitation() | CancelledElicitation():
            return {"deleted": False, "reason": "Confirmation was declined or dismissed."}

if __name__ == "__main__":
    log.info("webex-troubleshooting-complex running on stdio - waiting for a client (Ctrl+C to stop).")
    try:
        mcp.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
