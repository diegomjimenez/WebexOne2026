import os
import sys
import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

load_dotenv()
TOKEN = os.environ.get("ACCESS_TOKEN")

if not TOKEN:
    sys.exit("ACCESS_TOKEN is not set. Please set it in your .env file.")

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

mcp = MCPServer("webex-calling-hub")

@mcp.tool()
async def list_numbers(max_results: int = 25) -> dict:
    """List phone numbers configured in the organization."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://webexapis.com/v1/telephony/config/numbers",
            headers=HEADERS,
            params={"max": max_results}
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    numbers = r.json().get("phoneNumbers", [])
    return {
        "count": len(numbers),
        "numbers": [
            {"number": n.get("phoneNumber"), "state": n.get("state"), "location": n.get("location", {}).get("name")}
            for n in numbers
        ]
    }

@mcp.tool()
async def list_people(max_results: int = 10) -> dict:
    """List users (people) in the organization."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(
            "https://webexapis.com/v1/people",
            headers=HEADERS,
            params={"max": max_results}
        )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    people = r.json().get("items", [])
    return {
        "count": len(people),
        "people": [
            {"id": p.get("id"), "emails": p.get("emails"), "displayName": p.get("displayName")}
            for p in people
        ]
    }

@mcp.tool()
async def unresolved_incidents() -> dict:
    """Check Webex for any unresolved platform incidents."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get("https://status.webex.com/api/v2/incidents/unresolved.json")
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    
    incidents = r.json().get("incidents", [])
    return {"count": len(incidents), "incidents": incidents}

if __name__ == "__main__":
    print("webex-calling-hub running on stdio.", file=sys.stderr)
    mcp.run()
