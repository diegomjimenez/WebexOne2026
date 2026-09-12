"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 07 - second capstone: the same four MCP primitives as 06, but for
# Contact Center AGENTS instead of address books. prompt + resource + read
# tools + an elicitation-gated write. Logs go to 07_agents_server.log only.
# diff 06_full_server.py 07_agents_server.py to see the agent-specific changes.

import logging
import os
import sys
from pathlib import Path
from typing import Annotated

import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

# Elicitation imports for the write tool (reassign_desktop_profile).
from mcp.server.mcpserver import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
    Elicit,
    ElicitationResult,
    Resolve,
)
from pydantic import BaseModel

# Configure file-only logging (not stderr) so the terminal stays clean.
_LOG_FILE = Path(__file__).parent / "07_agents_server.log"
logging.basicConfig(
    filename=str(_LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("webex")

# Load credentials from .env.
load_dotenv()

TOKEN = os.environ.get("WEBEX_ACCESS_TOKEN")
ORG_ID = os.environ.get("WEBEX_ORG_ID")
CONFIG_API_BASE = os.environ.get("WXCC_CONFIG_API_BASE", "")

# Stop early if any credential is missing.
for _name, _value in (
    ("WEBEX_ACCESS_TOKEN", TOKEN),
    ("WEBEX_ORG_ID", ORG_ID),
    ("WXCC_CONFIG_API_BASE", CONFIG_API_BASE),
):
    if not _value:
        sys.exit(f"{_name} is not set. See .env.example.")

# Build the API base URL and common headers (same base/auth as 06).
ORG = f"{CONFIG_API_BASE.rstrip('/')}/organization/{ORG_ID}"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

# WXCC Config API paths for agents — the ONE place to adjust per tenant.
# In WXCC, an "agent" is a user; a "desktop profile" governs what the agent
# can do. Confirm these against your org before a live demo (see change
# task 1.1); the shapes below match the {"data": [...]} style 06 uses.
USER_PATH = "/user"                        # list/get users (agents)
DESKTOP_PROFILE_PATH = "/desktop-profile"  # list/get desktop profiles
TEAM_PATH = "/team"                        # list teams

# Create an MCP server instance.
mcp = MCPServer("webex-mcp-lab-07-agents")


# The confirmation form for the write operation.
class Confirm(BaseModel):
    ok: bool


# Resolver for desktop-profile reassignment.
async def confirm_reassign(agent_id: str, desktop_profile_id: str) -> Elicit[Confirm]:
    return Elicit(
        f"Reassign agent '{agent_id}' to desktop profile "
        f"'{desktop_profile_id}'? This changes what the agent can do.",
        Confirm,
    )


# Register a prompt that orchestrates the agent-availability diagnosis.
@mcp.prompt()
def diagnose_agent_availability(team: str = "", agent: str = "") -> str:
    """Diagnose why Contact Center agents appear offline or unavailable."""
    log.debug("diagnose_agent_availability prompt invoked (team=%r, agent=%r)", team, agent)
    return (
        f"Diagnose availability for the {team or '<team>'} team"
        f"{f' (agent {agent})' if agent else ''}.\n\n"
        "1. Read the lab://agent-troubleshooting resource and follow it.\n"
        "2. Call list_teams and list_agents to see who is configured.\n"
        "3. For each affected agent, call get_desktop_profile on their profile.\n"
        "4. Compare the profile assignment against the expected queue config.\n"
        "5. Summarize the findings and recommend next actions.\n"
        "Never reassign a profile without explicit user approval."
    )


# Register a resource with the house style for agent troubleshooting.
@mcp.resource("lab://agent-troubleshooting")
def agent_troubleshooting_conventions() -> str:
    """House style for diagnosing agent state in this organization."""
    log.debug("agent_troubleshooting_conventions resource read")
    return (
        "# Agent troubleshooting reference\n"
        "\n"
        "## State glossary\n"
        "- Not Ready: the agent is logged in but idle-coded or has a stale session.\n"
        "- Reserved: the agent is being offered a contact; transitions automatically.\n"
        "- Available: the agent is ready and in a queue to receive contacts.\n"
        "- Missing from roster: the agent's team or site assignment is wrong.\n"
        "\n"
        "## Severity rubric\n"
        "- HIGH: empty address book used for routing, or an entire team offline.\n"
        "- LOW: a single agent stuck in Not Ready (usually an idle-code issue).\n"
        "\n"
        "## Escalation policy\n"
        "- Contact: the Webex Contact Center administrator for the org.\n"
        "- Required info: agent email, exact dashboard state, first-seen time.\n"
        "\n"
        "## Facts\n"
        "- Config changes can take a few minutes to propagate — note the timing.\n"
        "- Profile changes (reassign or delete) require explicit user approval.\n"
    )


# List the agents (users) configured in the Contact Center organization.
@mcp.tool()
async def list_agents(limit: int = 50) -> dict:
    """List the agents (users) configured in this Contact Center organization."""
    log.debug("list_agents: GET %s%s", ORG, USER_PATH)
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(f"{ORG}{USER_PATH}", headers=HEADERS, params={"pageSize": limit})
    log.debug("list_agents: HTTP %s", r.status_code)
    if r.status_code != 200:
        return {"error": f"Webex Contact Center returned HTTP {r.status_code}."}
    # /user may return a bare list or {"data": [...]}, handle both.
    body = r.json()
    items = body if isinstance(body, list) else body.get("data", [])
    agents = [
        {
            "id": a.get("id"),
            "name": a.get("displayName") or a.get("email"),
            "desktop_profile_id": a.get("agentProfileId") or a.get("desktopProfileId"),
        }
        for a in items
    ]
    return {"count": len(agents), "agents": agents}


# Get a single desktop profile by id.
@mcp.tool()
async def get_desktop_profile(desktop_profile_id: str) -> dict:
    """Get one desktop profile by id, to compare against expected queue config."""
    log.debug("get_desktop_profile: GET %s%s/%s", ORG, DESKTOP_PROFILE_PATH, desktop_profile_id)
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(f"{ORG}{DESKTOP_PROFILE_PATH}/{desktop_profile_id}", headers=HEADERS)
    log.debug("get_desktop_profile: HTTP %s", r.status_code)
    if r.status_code != 200:
        return {"error": f"Webex Contact Center returned HTTP {r.status_code}."}
    p = r.json()
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "description": p.get("description"),
    }


# List the teams configured in the Contact Center organization.
@mcp.tool()
async def list_teams(limit: int = 50) -> dict:
    """List the teams configured in this Contact Center organization."""
    log.debug("list_teams: GET %s%s", ORG, TEAM_PATH)
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(f"{ORG}{TEAM_PATH}", headers=HEADERS, params={"pageSize": limit})
    log.debug("list_teams: HTTP %s", r.status_code)
    if r.status_code != 200:
        return {"error": f"Webex Contact Center returned HTTP {r.status_code}."}
    # /team may return a bare list or {"data": [...]}, handle both.
    body = r.json()
    items = body if isinstance(body, list) else body.get("data", [])
    teams = [
        {"id": t.get("id"), "name": t.get("name")}
        for t in items
    ]
    return {"count": len(teams), "teams": teams}


# Reassign an agent's desktop profile after the user confirms via elicitation.
@mcp.tool()
async def reassign_desktop_profile(
    agent_id: str,
    desktop_profile_id: str,
    confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_reassign)],
) -> dict:
    """Reassign an agent to a desktop profile. The server asks you to confirm first."""
    match confirm:
        case AcceptedElicitation(data=Confirm(ok=True)):
            # WXCC updates a user with the full object, so read-then-write.
            log.debug("reassign_desktop_profile: GET %s%s/%s", ORG, USER_PATH, agent_id)
            async with httpx.AsyncClient(timeout=15) as http:
                got = await http.get(f"{ORG}{USER_PATH}/{agent_id}", headers=HEADERS)
                if got.status_code != 200:
                    return {"error": f"Could not read agent (HTTP {got.status_code})."}
                agent = got.json()
                agent["agentProfileId"] = desktop_profile_id
                log.debug("reassign_desktop_profile: PUT %s%s/%s", ORG, USER_PATH, agent_id)
                r = await http.put(
                    f"{ORG}{USER_PATH}/{agent_id}", headers=HEADERS, json=agent
                )
            log.debug("reassign_desktop_profile: HTTP %s", r.status_code)
            if r.status_code not in (200, 201):
                return {"error": f"Webex Contact Center returned HTTP {r.status_code}."}
            return {"reassigned": True, "agent_id": agent_id,
                    "desktop_profile_id": desktop_profile_id}
        case AcceptedElicitation():
            return {"reassigned": False, "reason": "You chose not to reassign."}
        case DeclinedElicitation() | CancelledElicitation():
            return {"reassigned": False, "reason": "Confirmation was declined or dismissed."}


# Start the server on stdio and wait for a client to connect.
if __name__ == "__main__":
    print(
        "webex-mcp-lab-07-agents running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
