"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Local tools module — tools the bot offers that do NOT come from the MCP server.
# The agentic loop already merges these via extra_tools + dispatch (same path
# skills_loader uses for load_skill), so a skill can orchestrate a local tool
# and an MCP tool in one flow. This one checks the public Webex status page.

import logging

import requests

log = logging.getLogger(__name__)

# Public Webex status feed (Statuspage JSON — no auth, no org scope).
# index.json carries {status:{indicator}, incidents:[...]}.
_STATUS_URL = "https://status.webex.com/index.json"

# Map the Statuspage indicator to a human-readable phrase for the model.
_INDICATOR_TEXT = {
    "none": "All systems operational",
    "green": "All systems operational",
    "minor": "Minor service issue",
    "major": "Major service outage",
    "critical": "Critical service outage",
}


# Query the public Webex status page and return a concise, model-friendly summary.
def check_webex_status() -> str:
    """Return a one-line Webex platform status, or a safe fallback on any error."""
    try:
        resp = requests.get(_STATUS_URL, timeout=10)
        if not resp.ok:
            return f"Webex status unavailable (HTTP {resp.status_code})."
        data = resp.json()
        indicator = data.get("status", {}).get("indicator", "unknown")
        description = _INDICATOR_TEXT.get(indicator, "Status unknown")
        # List any unresolved incidents so the model can weigh them.
        incidents = [i.get("name", "incident") for i in data.get("incidents", [])]
        if incidents:
            return f"Webex status: {description} ({indicator}). Active: {', '.join(incidents)}."
        return f"Webex status: {description} ({indicator}). No active incidents."
    except Exception as exc:  # never raise into the agentic loop
        log.warning("check_webex_status failed: %s", exc)
        return "Webex status unavailable (could not reach status page)."


# OpenAI function spec for check_webex_status (pass inside extra_tools).
def status_tool_spec() -> dict:
    return {"type": "function", "function": {
        "name": "check_webex_status",
        "description": "Check the public Webex platform status for ongoing incidents. "
                       "Use this before blaming an agent's configuration.",
        "parameters": {"type": "object", "properties": {}},
    }}


# Dispatch entry for check_webex_status (merge into the agentic loop dispatch).
def status_dispatch() -> dict:
    return {"check_webex_status": lambda a: check_webex_status()}
