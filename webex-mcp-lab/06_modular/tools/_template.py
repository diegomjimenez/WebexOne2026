"""Template domain - copy this file to start a new Webex API family.

This is NOT a live domain. It is a starting point. To use it: copy this file to
`tools/<your_domain>.py`, rename the tool, point it at a real Webex endpoint,
and add your new module to the DOMAINS list in server.py. Until you do, it is
inert - it is deliberately absent from DOMAINS, so the running server is
unchanged, and its one tool returns placeholder data over no network.

It follows the same contract as every domain module here:

    def register(mcp, client) -> None

and the same two rules that keep domains independent:

  * a domain module never imports another domain module
  * a domain module never reads os.environ - ask the client instead
"""


def register(mcp, client) -> None:
    """Add this domain's tools to the server. Copied and renamed, this is your start."""

    @mcp.tool()
    async def example_lookup(query: str = "") -> dict:
        """Say in one line what this returns - the model reads this to decide when to call it.

        This is a placeholder. Replace the body below with a real Webex call;
        until then it returns fake data and touches no network.
        """
        # --- Replace everything below with your Webex endpoint -----------------
        # A real read-only tool looks like address_books.list_address_books:
        #
        #     from webex_client import failure
        #     response = await client.request("GET", f"{base}/<path>", params={...})
        #     if response.status_code != 200:
        #         return failure(response)
        #     items = response.json().get("items", [])
        #     return {"count": len(items), "items": [...keep only the fields that matter...]}
        #
        # Point `client.request` at Webex Calling, Meetings, or another Contact
        # Center API - the contract does not change, only the URL and the fields
        # you keep. For a write tool or extra credentials, copy the shapes in
        # address_books.py.
        #
        # You do not add any logging here: client.request already writes a DEBUG
        # line for the request and the response, so this domain is traced the
        # moment it makes its first real call.
        # -----------------------------------------------------------------------
        return {
            "placeholder": True,
            "note": "Template tool. Replace the body with a real Webex call.",
            "echo": query,
        }
