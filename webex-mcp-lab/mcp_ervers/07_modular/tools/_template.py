"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Template domain - copy this file to start a new Webex API family.
#
# Not wired into DOMAINS by default. To use it: copy to tools/<your_domain>.py,
# rename the tool, point it at a real Webex endpoint, and add the module to
# DOMAINS in server.py.


def register(mcp, client) -> None:
    """Add this domain's tools to the server. Copied and renamed, this is your start."""

    @mcp.tool()
    async def example_lookup(query: str = "") -> dict:
        """Say in one line what this returns - the model reads this to decide when to call it.

        This is a placeholder. Replace the body below with a real Webex call;
        until then it returns fake data and touches no network.
        """
        # A real read-only tool looks like address_books.list_address_books:
        #
        #     from webex_client import failure
        #     response = await client.request("GET", f"{base}/<path>", params={...})
        #     if response.status_code != 200:
        #         return failure(response)
        #     items = response.json().get("data", [])
        #     return {"count": len(items), "items": [...only fields that matter...]}
        #
        # client.request already writes DEBUG lines for request and response,
        # so this domain is traced the moment it makes its first real call.
        return {
            "placeholder": True,
            "note": "Template tool. Replace the body with a real Webex call.",
            "echo": query,
        }
