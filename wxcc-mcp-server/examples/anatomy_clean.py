import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("wxcc-mcp-server")

TOKEN = os.environ["WXCC_ACCESS_TOKEN"]


@mcp.tool()
async def list_agents(org_id: str, max_results: int = 50) -> dict:
    """List agents in a WxCC org with their desktop profile assignment."""

    resp = await httpx.AsyncClient(timeout=30).get(
        f"https://api.wxcc-us1.cisco.com/organization/{org_id}/user",
        headers={"Authorization": f"Bearer {TOKEN}"},
        params={"pageSize": max_results},
    )

    if resp.status_code == 429:
        return {"error": "Rate limit hit — retry in a moment."}
    if resp.status_code != 200:
        return {"error": f"WxCC API returned HTTP {resp.status_code}"}

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


if __name__ == "__main__":
    mcp.run()
