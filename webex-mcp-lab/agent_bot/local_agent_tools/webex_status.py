"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Webex status / incident check — a local agent tool the bot offers that does
# NOT come from the MCP server. Merged into the agentic loop via
# extra_tools + dispatch, so a skill can orchestrate local and MCP tools in
# one flow.

import logging
import requests

log = logging.getLogger(__name__)

# Public Webex status feed — no auth required. /index.json returns components,
# status, and incidents in ONE call (simpler for the lab than the /api/v2/*.json
# endpoints, which split the same data across several requests).
_STATUS_URL = "https://status.webex.com/status.json"


def check_webex_status() -> str:
    """Return Contact Center + platform status in one line."""
    try:
        data = requests.get(_STATUS_URL, timeout=10).json()
        # Contact Center components.
        cc = [c for c in data.get("components", [])
              if "contact center" in c.get("name", "").lower()]
        cc_line = ", ".join(f"{c['name']}: {c['status']}" for c in cc) or "no data"
        # Platform roll-up.
        indicator = data.get("status", {}).get("indicator", "unknown")
        incidents = [i["name"] for i in data.get("incidents", [])]
        inc_line = f"Active: {', '.join(incidents)}" if incidents else "No incidents"
        return f"CC: {cc_line}. Platform: {indicator}. {inc_line}."
    except Exception:
        return "Webex status unavailable."


# OpenAI function spec — pass inside extra_tools.
def status_tool_spec() -> dict:
    return {"type": "function", "function": {
        "name": "check_webex_status",
        "description": "Check the public Webex status page for platform or "
                       "Contact Center incidents. Call before investigating "
                       "agent configuration issues.",
        "parameters": {"type": "object", "properties": {}},
    }}


# Dispatch entry — merge into the agentic loop dispatch dict.
def status_dispatch() -> dict:
    return {"check_webex_status": lambda a: check_webex_status()}
