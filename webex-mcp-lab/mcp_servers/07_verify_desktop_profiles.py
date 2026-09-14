"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 07 - Desktop Profile Verification server.
# Focused on verifying agent-to-desktop-profile assignments.
# 1 resource (field glossary), 3 read tools, 1 write tool (elicitation).
# No prompts — troubleshooting logic lives in the client-side agent skill.
# Logs go to 07_verify_desktop_profiles.log only.

import logging
import os
import sys
from pathlib import Path
from typing import Annotated

import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

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
_LOG_FILE = Path(__file__).parent / "07_verify_desktop_profiles.log"
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

# WXCC Config API paths.
USER_PATH = "/user"                        # list/get users (agents)
DESKTOP_PROFILE_PATH = "/desktop-profile"  # list/get desktop profiles

# Create an MCP server instance.
mcp = MCPServer("verify-desktop-profiles")


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


# Register a resource with the desktop-profile field glossary.
@mcp.resource("lab://desktop-profile-reference")
def desktop_profile_reference() -> str:
    """Field glossary for desktop profiles and agent-to-profile mapping."""
    log.debug("desktop_profile_reference resource read")
    return (
        "# Desktop Profile Reference\n"
        "\n"
        "## What is a desktop profile?\n"
        "A desktop profile controls what an agent can do on the Agent Desktop.\n"
        "Each agent is assigned exactly one profile.\n"
        "\n"
        "## Key fields returned by list_desktop_profiles / get_desktop_profile\n"
        "- name: human-readable profile name\n"
        "- id: use this to match against an agent's agentProfileId\n"
        "- description: optional text describing the profile's purpose\n"
        "\n"
        "## What list_agents returns\n"
        "- id: agent identifier\n"
        "- name: displayName or email\n"
        "- desktop_profile_id: which desktop profile is assigned (agentProfileId)\n"
        "\n"
        "## Matching agents to profiles\n"
        "- An agent's desktop_profile_id maps to a desktop profile's id.\n"
        "- If desktop_profile_id is empty or points to a non-existent profile,\n"
        "  the agent may have default or no permissions.\n"
        "- The desktop profile determines which address books the agent can see.\n"
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


# List all desktop profiles in the organization.
@mcp.tool()
async def list_desktop_profiles(limit: int = 50) -> dict:
    """List all desktop profiles configured in this Contact Center organization."""
    log.debug("list_desktop_profiles: GET %s%s", ORG, DESKTOP_PROFILE_PATH)
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            f"{ORG}{DESKTOP_PROFILE_PATH}", headers=HEADERS, params={"pageSize": limit}
        )
    log.debug("list_desktop_profiles: HTTP %s", r.status_code)
    if r.status_code != 200:
        return {"error": f"Webex Contact Center returned HTTP {r.status_code}."}
    body = r.json()
    items = body if isinstance(body, list) else body.get("data", [])
    profiles = [
        {"id": p.get("id"), "name": p.get("name"), "description": p.get("description")}
        for p in items
    ]
    return {"count": len(profiles), "profiles": profiles}


# Get a single desktop profile by id.
@mcp.tool()
async def get_desktop_profile(desktop_profile_id: str) -> dict:
    """Get one desktop profile by id."""
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
        "verify-desktop-profiles running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
