"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
import asyncio
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
        r = await http.get("https://status.webex.com/unresolved-incidents.json")
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def list_security_audit_events(days_back: int = 7, max_results: int = 10) -> dict:
    """List recent security audit events (user sign-ins and sign-outs) in the organization."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=days_back)
    
    params = {
        "orgId": ORG_ID,
        "startTime": past.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "endTime": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "max": max_results
    }
    
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://webexapis.com/v1/admin/securityAudit/events",
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
                "actorEmail": e.get("data", {}).get("actorEmail"),
                "clientIP": e.get("data", {}).get("clientIP"),
                "eventCategory": e.get("data", {}).get("eventCategory"),
                "eventDescription": e.get("data", {}).get("eventDescription"),
            }
            for e in events
        ]
    }

@mcp.tool()
async def list_reports() -> dict:
    """List recent usage and activity reports generated in the organization."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get("https://webexapis.com/v1/reports", headers=HEADERS)
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

def _parse_cdr_time(value: str) -> datetime:
    """Parse a CDR window bound. Accepts 'YYYY-MM-DD' (start of that UTC day)
    or a full ISO 8601 timestamp such as '2026-09-24T05:00:00Z'."""
    text = value.strip()
    if len(text) == 10:  # date only -> start of day UTC
        text += "T00:00:00+00:00"
    else:
        text = text.replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@mcp.tool()
async def get_detailed_call_history(hours_back: int = 12, max_results: int = 500,
                                    start_time: str = "", end_time: str = "") -> dict:
    """Get Webex Calling CDRs (call detail records).

    Pick the window from the request:
    1. The user names ANY date or time (e.g. "on 2026-09-24 between 05:00 and
       08:30 UTC", "yesterday morning", "last Tuesday"): you MUST pass
       `start_time` and `end_time` as absolute UTC values. Do NOT leave them empty
       and do NOT use `hours_back` for a dated request — that returns the last 12
       hours ending now and misses the window entirely. Past dates are fully
       supported. Accepts 'YYYY-MM-DD' or ISO 8601. Example: for "2026-09-24
       between 05:00 and 08:30 UTC" pass start_time="2026-09-24T05:00:00Z",
       end_time="2026-09-24T08:30:00Z".
    2. Only when the user gives no date and just wants recent calls: leave
       start_time/end_time empty and use `hours_back` (1-12, default 12).

    The tool automatically enforces the maximum 12-hour span.

    Rate limit: call this at most once per user request. The CDR feed allows
    roughly one request per minute; a second call returns 429 Too Many Requests.
    """
    max_results = max(500, min(max_results, 5000))
    latest = datetime.now(timezone.utc) - timedelta(minutes=6)
    if start_time or end_time:
        try:
            end = _parse_cdr_time(end_time) if end_time \
                else _parse_cdr_time(start_time) + timedelta(hours=12)
            start = _parse_cdr_time(start_time) if start_time \
                else end - timedelta(hours=12)
        except ValueError:
            return {"error": "start_time/end_time must be 'YYYY-MM-DD' or ISO 8601 (e.g. 2026-09-24T05:00:00Z)."}
        if end > latest:
            end = latest
        if end - start > timedelta(hours=12):
            start = end - timedelta(hours=12)
        if start >= end:
            return {"error": "start_time must be before end_time (and end_time at least ~5 minutes in the past)."}
    else:
        hours_back = max(1, min(hours_back, 12))
        end = latest
        start = end - timedelta(hours=hours_back)
    params = {
        "startTime": start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "endTime": end.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "max": max_results
    }
    async with httpx.AsyncClient(timeout=15) as http:
        # The CDR feed is rate-limited to ~1 request/min. If we get a 429,
        # wait (honoring Retry-After when present) and retry once.
        for attempt in range(2):
            r = await http.get(
                "https://analytics-calling.webexapis.com/v1/cdr_feed",
                headers=HEADERS,
                params=params
            )
            if r.status_code != 429 or attempt == 1:
                break
            retry_after = r.headers.get("Retry-After", "")
            wait = min(int(retry_after), 65) if retry_after.isdigit() else 60
            log.info("CDR feed returned 429; waiting %ss before one retry.", wait)
            await asyncio.sleep(wait)
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    records = r.json().get("items", [])
    return {
        "count": len(records),
        "startTime": params["startTime"],
        "endTime": params["endTime"],
        "calls": [
            {
                "reportId": record.get("Report ID"),
                "startTime": record.get("Start time"),
                "releaseTime": record.get("Release time"),
                "duration": record.get("Duration"),
                "direction": record.get("Direction"),
                "callType": record.get("Call type"),
                "callingNumber": record.get("Calling number"),
                "calledNumber": record.get("Called number"),
                "answered": record.get("Answered"),
                "outcome": record.get("Call outcome"),
                "outcomeReason": record.get("Call outcome reason"),
                "user": record.get("User"),
                "location": record.get("Location"),
            }
            for record in records
        ]
    }

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
async def list_ended_meetings(days_back: int = 30, max_results: int = 25,
                              host_email: str = "") -> dict:
    """List meetings that already ended, so their IDs can be used for quality analysis.

    `days_back` is how far back to look (default 30). When the user names a window
    ("last 7 days", "this month", "last 60 days"), pass that number here — do NOT
    rely on the default. Meeting history is often sparse, so prefer a wide window
    when the user does not specify one.

    `host_email` scopes the list to meetings hosted by one person. When the user
    asks about a specific user ("meetings <someone> hosted", "<someone>'s
    meetings"), pass their email here instead of listing the whole org — that is
    the realistic, targeted query. Requires admin rights over that user."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=max(1, days_back))
    params = {
        "meetingType": "meeting",
        "state": "ended",
        "from": past.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max": max_results
    }
    if host_email:
        params["hostEmail"] = host_email
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get("https://webexapis.com/v1/meetings", headers=HEADERS, params=params)
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def get_meeting_qualities(meeting_id: str) -> dict:
    """Analytics and diagnostics for an ended meeting. Use the ID from list_ended_meetings."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get("https://analytics.webexapis.com/v1/meeting/qualities", headers=HEADERS, params={"meetingId": meeting_id})
    return r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text}"}

@mcp.tool()
async def list_meeting_participants(meeting_id: str) -> dict:
    """Who attended an ended meeting and when. Returns each participant with their
    join/leave times and per-device audio type. Use the ID from list_ended_meetings.
    Pair with get_meeting_qualities to tie a quality dip to who was in the room then."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://webexapis.com/v1/meetingParticipants",
            headers=HEADERS,
            params={"meetingId": meeting_id},
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    items = r.json().get("items", [])
    return {
        "count": len(items),
        "participants": [
            {
                "displayName": p.get("displayName"),
                "email": p.get("email"),
                "host": p.get("host"),
                "coHost": p.get("coHost"),
                "state": p.get("state"),
                "joinedTime": p.get("joinedTime"),
                "leftTime": p.get("leftTime"),
                "devices": [
                    {
                        "deviceType": d.get("deviceType"),
                        "audioType": d.get("audioType"),
                        "joinedTime": d.get("joinedTime"),
                        "leftTime": d.get("leftTime"),
                    }
                    for d in (p.get("devices") or [])
                ],
            }
            for p in items
        ],
    }

@mcp.tool()
async def list_report_templates(service: str = "") -> dict:
    """List report templates. Org-level templates need only dates. Meetings (identifier 'site') also need siteList."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get("https://webexapis.com/v1/report/templates", headers=HEADERS)
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    templates = r.json().get("items", [])
    if service:
        templates = [t for t in templates if service.lower() in (t.get("service") or "").lower()]
    return {
        "count": len(templates),
        "templates": [
            {"id": t.get("Id"), "title": t.get("title"), "service": t.get("service"), "identifier": t.get("identifier")}
            for t in templates
        ]
    }

@mcp.tool()
async def create_report(template_id: str, start_date: str, end_date: str, site_list: str = "") -> dict:
    """Create a report. Dates must be YYYY-MM-DD. For Meetings templates, pass site_list as a comma-separated site URL."""
    payload = {
        "templateId": int(template_id) if template_id.isdigit() else template_id,
        "startDate": start_date,
        "endDate": end_date
    }
    if site_list:
        payload["siteList"] = [s.strip() for s in site_list.split(",") if s.strip()]
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
