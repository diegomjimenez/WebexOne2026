"""Address book domain - the whole lab, in the shape a server keeps.

This one module registers all three MCP primitives for Contact Center address
books: four tools, one resource, and one prompt. It is the modular form of
chapters 02-05.

Needs a Contact Center organization and a token carrying cjp:config_read and
cjp:config_write. It asks for its extra credentials at registration time, so a
misconfiguration is reported once at startup, not once per tool call.

No delete tools. Address books are shared configuration, so the destructive
verbs are left out on purpose.
"""

from webex_client import failure


def register(mcp, client) -> None:
    """Add this domain's tools, resource, and prompt to the server."""

    # Asking for the extra credentials here means a misconfiguration is reported
    # once, at startup, naming both the missing variable and this domain.
    settings = client.require(
        "WEBEX_ORG_ID", "WXCC_CONFIG_API_BASE", needed_by="the address book domain"
    )
    base = settings["WXCC_CONFIG_API_BASE"].rstrip("/")
    org = f"{base}/organization/{settings['WEBEX_ORG_ID']}"

    @mcp.resource("webex://address-books/conventions")
    def address_book_conventions() -> str:
        """House style for address books in this organization."""
        return (
            "# Address book conventions\n"
            "\n"
            "- Name a book for its team or purpose, e.g. 'Sales - EMEA', not 'Book1'.\n"
            "- Before creating a book, list existing books and reuse one if it fits.\n"
            "- Store numbers in E.164 format: a leading +, country code, no spaces,\n"
            "  e.g. +14155550101.\n"
            "- Give every entry a human name; never add a bare number.\n"
        )

    @mcp.prompt()
    def set_up_address_book(book_name: str = "", team: str = "") -> str:
        """Set up an address book end to end: create it and add its first contacts."""
        return (
            f"Set up an address book called {book_name or '<book name>'} for the "
            f"{team or '<team>'} team.\n"
            "\n"
            "1. Read the webex://address-books/conventions resource and follow it.\n"
            "2. Call list_address_books first - reuse a matching book, do not duplicate.\n"
            "3. Otherwise call create_address_book and keep the id it returns.\n"
            "4. Ask me for the contacts (name and E.164 number each).\n"
            "5. Show me the list and, once I approve, call add_entry for each."
        )

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
        """Create a new address book. Returns its id, which add_entry then needs.

        Your MCP client asks for approval first.
        """
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

        # Listing entries is the one operation on v2; the others below vary too.
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
