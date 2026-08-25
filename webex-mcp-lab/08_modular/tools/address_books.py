"""Address book domain - Webex Contact Center configuration, from step 07.

Needs more than the base token: a Contact Center organization, and a token
carrying cjp:config_read and cjp:config_write. If you do not have one, remove
this module from the DOMAINS list in server.py and everything else still runs.

No delete tools. Address books are shared configuration, so the destructive
verbs are left out on purpose.
"""

import sys

from webex_client import failure


def register(mcp, client) -> None:
    """Add this domain's tools to the server."""

    # Asking for the extra credentials here means a misconfiguration is
    # reported once, at startup, instead of once per tool call.
    settings = client.require(
        "WEBEX_ORG_ID", "WEBEX_CC_API_BASE", needed_by="the address book domain"
    )
    base = settings["WEBEX_CC_API_BASE"].rstrip("/")
    if "REGION" in base:
        sys.exit("WEBEX_CC_API_BASE still says REGION. Replace it with your data centre.")
    org = f"{base}/organization/{settings['WEBEX_ORG_ID']}"

    @mcp.tool()
    async def list_address_books(limit: int = 50) -> dict:
        """List the address books configured in this Contact Center organization."""
        response = await client.request(
            "GET", f"{org}/v3/address-book", params={"pageSize": limit}
        )
        if response.status_code != 200:
            return failure(response)

        books = [
            {"id": b.get("id"), "name": b.get("name"), "description": b.get("description")}
            for b in response.json().get("items", [])
        ]
        return {"count": len(books), "address_books": books}

    @mcp.tool()
    async def create_address_book(name: str, description: str = "") -> dict:
        """Create a new address book. Your MCP client asks for approval first."""
        response = await client.request(
            "POST",
            f"{org}/v3/address-book",
            json={"name": name, "description": description, "parentType": "ORGANIZATION"},
        )
        if response.status_code not in (200, 201):
            return failure(response)

        book = response.json()
        return {"created": True, "address_book_id": book.get("id"), "name": book.get("name")}

    @mcp.tool()
    async def list_entries(address_book_id: str, search: str = "") -> dict:
        """List the contacts inside one address book, optionally filtered by `search`."""
        params: dict = {"page": 0, "pageSize": 100}
        if search:
            params["search"] = search

        # Listing entries is the one operation on v2; creating is still v1.
        response = await client.request(
            "GET", f"{org}/v2/address-book/{address_book_id}/entry", params=params
        )
        if response.status_code != 200:
            return failure(response)

        entries = [
            {"id": e.get("id"), "name": e.get("name"), "number": e.get("number")}
            for e in response.json().get("items", [])
        ]
        return {"count": len(entries), "entries": entries}

    @mcp.tool()
    async def add_entry(address_book_id: str, name: str, number: str) -> dict:
        """Add a contact to an address book. `number` should be E.164, e.g. +14155550101.

        Your MCP client asks for approval before this runs.
        """
        response = await client.request(
            "POST",
            f"{org}/address-book/{address_book_id}/entry",
            json={"name": name, "number": number},
        )
        if response.status_code not in (200, 201):
            return failure(response)

        return {"added": True, "entry_id": response.json().get("id"), "name": name}
