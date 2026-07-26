"""Resource: crm_contacts.

A static snapshot of contact data as it might be exported from a CRM or corporate
directory. In a real deployment this would come from a live CRM API; for the lab
it is a deterministic JSON document that serves as the *source of truth* for the
``sync_crm_to_address_book`` flow.

The data is structured in two layers to support the lab narrative:

- **DAY1_CONTACTS** — the 3 contacts an admin adds manually on first setup.
- **CONTACTS** — the full Week 2 CRM export (7 contacts). Compared to Day 1:
  - 4 new contacts appeared (new accounts closed this week)
  - 1 existing number changed (Initech got a new DID)
  - 1 contact removed (Globex left the partner program — absent from this list)

The sync tool diffs CONTACTS against whatever is already in the address book,
making the "Monday Morning" chapter land: the admin added 3 by hand on Day 1,
but by Monday the CRM has 7 — with changes. Do that by hand every week?

Each contact has a stable ``id`` (used as the sync match key), a ``name``, and a
``number`` in E.164 format.
"""

from __future__ import annotations

from typing import Any

RESOURCE_URI = "crm://contacts"

# Day 1: the initial 3 contacts the admin adds manually during the lab.
DAY1_CONTACTS: list[dict[str, str]] = [
    {"id": "crm-1001", "name": "Acme Corp - Reception", "number": "+14155550101"},
    {"id": "crm-1003", "name": "Globex - Support Desk", "number": "+14155550103"},
    {"id": "crm-1004", "name": "Initech - Sales", "number": "+14155550104"},
]

# Week 2: the full CRM export as of "Monday morning". Differences from Day 1:
#   - crm-1002  NEW      Acme Corp - Billing (new department contact)
#   - crm-1004  UPDATED  Initech - Sales number changed (+14155550104 → +14155550184)
#   - crm-1005  NEW      Umbrella - Escalations
#   - crm-1006  NEW      Soylent - Accounts
#   - crm-1007  NEW      Hooli - Partner Line
#   - crm-1003  REMOVED  Globex left the partner program (absent from this list)
CONTACTS: list[dict[str, str]] = [
    {"id": "crm-1001", "name": "Acme Corp - Reception", "number": "+14155550101"},
    {"id": "crm-1002", "name": "Acme Corp - Billing", "number": "+14155550102"},
    {"id": "crm-1004", "name": "Initech - Sales", "number": "+14155550184"},
    {"id": "crm-1005", "name": "Umbrella - Escalations", "number": "+14155550105"},
    {"id": "crm-1006", "name": "Soylent - Accounts", "number": "+14155550106"},
    {"id": "crm-1007", "name": "Hooli - Partner Line", "number": "+14155550107"},
]


def get_day1_contacts() -> list[dict[str, str]]:
    """Return the Day 1 baseline contacts (manual-add set)."""
    return [dict(contact) for contact in DAY1_CONTACTS]


def get_contacts() -> list[dict[str, str]]:
    """Return the current CRM contact records (the sync source of truth)."""
    return [dict(contact) for contact in CONTACTS]


def as_dict() -> dict[str, Any]:
    """Return the CRM snapshot as a serializable dict (Week 2 state)."""
    return {
        "description": (
            "CRM/directory contact export — Week 2 state. Compared to Day 1: "
            "4 new contacts, 1 number update, 1 removal (Globex)."
        ),
        "source": "static-lab-fixture",
        "total": len(CONTACTS),
        "contacts": get_contacts(),
        "day1_baseline_count": len(DAY1_CONTACTS),
    }
