"""Anatomy of an MCP Tool — single-file teaching example."""

import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("wxcc-mcp-server")

# --- Credential Handling (Required) ------------------------------------------
# The token is loaded from the environment at startup. It's injected into API
# calls internally and never surfaces in tool inputs, outputs, or logs.
TOKEN = os.environ["WXCC_ACCESS_TOKEN"]


# --- Tool Catalog (Required) -------------------------------------------------
# The decorator registers the tool. MCP clients discover it by name, read the
# docstring as the description, and derive the input schema from the signature.
@mcp.tool()
async def list_agents(org_id: str, max_results: int = 50) -> dict:
    """List agents in a WxCC org with their desktop profile assignment."""

    # --- Tool Execution (Required) --------------------------------------------
    # A straightforward API call. The token goes in the header; the LLM only
    # sees the structured result below — never the raw HTTP exchange.
    resp = await httpx.AsyncClient(timeout=30).get(
        f"https://api.wxcc-us1.cisco.com/organization/{org_id}/user",
        headers={"Authorization": f"Bearer {TOKEN}"},
        params={"pageSize": max_results},
    )

    # --- Operational Controls (Optional) --------------------------------------
    # Handle rate-limits and errors gracefully so the model gets a useful message
    # instead of a stack trace.
    if resp.status_code == 429:
        return {"error": "Rate limit hit — retry in a moment."}
    if resp.status_code != 200:
        return {"error": f"WxCC API returned HTTP {resp.status_code}"}

    # --- Response Formatting (Optional) ---------------------------------------
    # Return only what the model needs: a clean, filtered JSON structure.
    agents = [
        {
            "id": a.get("id"),
            "email": a.get("email"),
            "name": f'{a.get("firstName", "")} {a.get("lastName", "")}'.strip(),
            "profile_id": a.get("desktopProfileId"),
        }
        for a in resp.json().get("data", [])
    ]

    return {"org_id": org_id, "count": len(agents), "agents": agents}


# --- Guardrails (Optional) ---------------------------------------------------
# For read tools: input types enforce validation (str, int with bounds).
# For write tools: add a dry-run preview + explicit user approval before commit.

if __name__ == "__main__":
    mcp.run()
