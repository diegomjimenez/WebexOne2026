"""Anatomy of an MCP Resource — single-file teaching example."""

import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("wxcc-mcp-server")

PARENT_TYPES = [
    {"value": "CUSTOMER", "meaning": "Address book available org-wide"},
    {"value": "SITE", "meaning": "Address book scoped to one site"},
]

FIELD_RULES = [
    {"field": "name", "rule": "Required. Unique within the org."},
    {"field": "parentType", "rule": "CUSTOMER or SITE."},
    {"field": "entry number", "rule": "E.164 format: +14155551234"},
]


@mcp.resource("wxcc://reference/address-book-rules")
def address_book_rules() -> str:
    """Field rules and valid parent types for WxCC address books."""
    return json.dumps(
        {"parent_types": PARENT_TYPES, "field_rules": FIELD_RULES},
        indent=2,
    )


@mcp.tool()
async def create_address_book(
    org_id: str, name: str, parent_type: str
) -> dict:
    """Create an address book (the model already read the rules above)."""
    if parent_type not in ("CUSTOMER", "SITE"):
        return {"error": f"Invalid parentType: {parent_type}"}
    return {"org_id": org_id, "name": name, "parent_type": parent_type, "created": True}


if __name__ == "__main__":
    mcp.run()
