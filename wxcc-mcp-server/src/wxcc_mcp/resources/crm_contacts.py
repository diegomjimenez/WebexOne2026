"""Resource: crm_contacts.

A static snapshot of contact data as it might be exported from a CRM or corporate
directory. In a real deployment this would come from a live CRM API; for the lab
it is a deterministic JSON document that serves as the *source of truth* for the
``sync_crm_to_address_book`` flow.

Each contact has a stable ``id`` (used as the sync match key), a ``name``, and a
``number`` in E.164 format.
"""

from __future__ import annotations

from typing import Any

RESOURCE_URI = "crm://contacts"

CONTACTS: list[dict[str, str]] = [
    {"id": "crm-1001", "name": "Acme Corp — Reception", "number": "+14155550101"},
    {"id": "crm-1002", "name": "Acme Corp — Billing", "number": "+14155550102"},
    {"id": "crm-1003", "name": "Globex — Support Desk", "number": "+14155550103"},
    {"id": "crm-1004", "name": "Initech — Sales", "number": "+14155550104"},
    {"id": "crm-1005", "name": "Umbrella — Escalations", "number": "+14155550105"},
    {"id": "crm-1006", "name": "Soylent — Accounts", "number": "+14155550106"},
    {"id": "crm-1007", "name": "Hooli — Partner Line", "number": "+14155550107"},
]


def get_contacts() -> list[dict[str, str]]:
    """Return the CRM contact records (the sync source of truth)."""
    return [dict(contact) for contact in CONTACTS]


def as_dict() -> dict[str, Any]:
    """Return the CRM snapshot as a serializable dict."""
    return {
        "description": "Sample CRM/directory contact export used as the sync source.",
        "source": "static-lab-fixture",
        "total": len(CONTACTS),
        "contacts": get_contacts(),
    }
