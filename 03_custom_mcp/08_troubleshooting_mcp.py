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
        r = await http.get("https://status.webex.com/api/v2/incidents/unresolved.json")
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
            {"id": e.get("id"), "actionText": e.get("actionText"), "actorOrgName": e.get("actorOrgName"), "created": e.get("created")}
            for e in events
        ]
    }

if __name__ == "__main__":
    log.info("webex-troubleshooting-mcp running on stdio - waiting for a client (Ctrl+C to stop).")
    try:
        mcp.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
