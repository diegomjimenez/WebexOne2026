import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("wxcc-mcp-server")

TOKEN = os.environ["WXCC_ACCESS_TOKEN"]


@mcp.prompt()
def provision_outbound_dialing(org_id: str) -> str:
    """Provision outbound dialing for agents in a WxCC organization."""

    return f"""You are a Webex Contact Center administrator assistant for org "{org_id}".

TASK: Create an address book and assign it to a desktop profile so agents can dial out.

── STEP 1 ─────────────────────────────────────────────────────────────────────
Call `list_address_books` to check what already exists.
If none fits, call `create_address_book` with name and parent_type.

── STEP 2 ─────────────────────────────────────────────────────────────────────
Call `list_desktop_profiles` and help the admin pick which profile to provision.
Show how many agents are assigned to each profile.

── STEP 3 ─────────────────────────────────────────────────────────────────────
Call `assign_address_book_to_profile` to link the book to the chosen profile.
Preview first, commit only on admin approval.

── STEP 4 ─────────────────────────────────────────────────────────────────────
Verify by calling `get_desktop_profile` and confirm the assignment took effect.

── OUTPUT FORMAT ───────────────────────────────────────────────────────────────
Return a structured summary with: address book name/id, profile name/id, agent count.

── EXAMPLE ─────────────────────────────────────────────────────────────────────
Admin: "Set up outbound dialing for my sales team."

Assistant response after completing all steps:
  Done. Address book "Sales Contacts" (ab-123) is now assigned to profile
  "Outbound Team" (dp-456). 12 agents have outbound dial access.

── QUALITY CRITERIA ────────────────────────────────────────────────────────────
- NEVER commit a write without explicit admin approval.
- If any step fails, STOP and report the error.
- Verify the final state before declaring success.
"""


@mcp.tool()
async def list_address_books(org_id: str) -> dict:
    """List address books in a WxCC organization."""

    resp = await httpx.AsyncClient(timeout=30).get(
        f"https://api.wxcc-us1.cisco.com/organization/{org_id}/address-book",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    if resp.status_code != 200:
        return {"error": f"API returned HTTP {resp.status_code}"}

    books = [
        {"id": b.get("id"), "name": b.get("name")}
        for b in resp.json().get("data", [])
    ]

    return {"org_id": org_id, "count": len(books), "address_books": books}


if __name__ == "__main__":
    mcp.run()
