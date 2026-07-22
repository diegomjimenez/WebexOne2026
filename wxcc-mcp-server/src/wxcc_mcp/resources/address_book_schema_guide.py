"""Resource: address_book_schema_guide.

Reference document the assistant can read to understand address-book and entry
rules before creating or syncing data: entry naming conventions, E.164 phone
formatting, and the meaning of an address book's ``parentType``.
"""

from __future__ import annotations

from typing import Any

RESOURCE_URI = "wxcc://reference/address-book-schema"

PARENT_TYPES: list[dict[str, str]] = [
    {
        "parent_type": "CUSTOMER",
        "meaning": "The address book is available organization-wide (all sites).",
    },
    {
        "parent_type": "SITE",
        "meaning": "The address book is scoped to a specific site in the organization.",
    },
]

FIELD_RULES: list[dict[str, str]] = [
    {
        "field": "address book name",
        "rule": "Required. Human-readable and unique within the org; keep it descriptive "
        "(e.g. 'CRM — Enterprise Accounts').",
    },
    {
        "field": "address book parentType",
        "rule": "Required. One of CUSTOMER (org-wide) or SITE (site-scoped).",
    },
    {
        "field": "entry name",
        "rule": "Required. The label agents see in the dial list; keep it concise.",
    },
    {
        "field": "entry number",
        "rule": "Required. Must be E.164: a leading '+', country code, then subscriber "
        "number, digits only (e.g. +14155551234). No spaces, dashes, or parentheses.",
    },
]

SYNC_NOTES: list[str] = [
    "Entries are matched to CRM contacts by a stable CRM id when available, else by "
    "normalized E.164 number.",
    "Pruning (deleting entries not present in the CRM source) is OFF by default and is a "
    "HIGH-risk action requiring explicit approval.",
    "An address book only reaches agents once it is assigned to a Desktop Profile "
    "(addressBookId) that those agents use.",
]


def as_dict() -> dict[str, Any]:
    """Return the schema guide as a serializable dict."""
    return {
        "description": "Rules for address books and entries: naming, E.164, parentType.",
        "parent_types": PARENT_TYPES,
        "field_rules": FIELD_RULES,
        "sync_notes": SYNC_NOTES,
    }
