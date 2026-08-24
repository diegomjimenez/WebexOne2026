"""Resource: write_safety_guide.

Policies and patterns for safely executing write operations in WxCC via the
MCP tool suite — covering the elicitation/dry-run pattern, approval gates,
rollback, and operation-specific risk levels. Only references tools that ship
in this lab's curated tool set (address books, entries, desktop profiles).
"""

from __future__ import annotations

from typing import Any

RESOURCE_URI = "wxcc://reference/write-safety-guide"

SAFETY_PRINCIPLES: list[dict[str, str]] = [
    {
        "principle": "Ask Before You Commit",
        "description": (
            "Every write tool is gated. The server asks the admin to approve the "
            "write interactively: accepting the prompt IS the approval, and "
            "declining or cancelling is final — it returns a dry-run preview and "
            "cannot be overridden by an argument. Invoke write tools without the "
            "confirm flag and let the prompt decide. On a client that cannot "
            "prompt at all, no approval can be requested and confirm becomes the "
            "only way to commit — the result says so explicitly when that "
            "happens, and asks for confirm once the admin has agreed in "
            "conversation. Setting it never skips a prompt that could be shown."
        ),
    },
    {
        "principle": "Dry-Run Reveals the Impact",
        "description": (
            "A dry-run returns a preview payload WITHOUT making any change. For a sync, "
            "the preview includes the exact counts to create, update, and delete. Always "
            "show the preview to the admin so they understand exactly what will change."
        ),
    },
    {
        "principle": "Pruning Is Opt-In",
        "description": (
            "The CRM sync never deletes entries unless pruning is explicitly enabled. "
            "Pruning is HIGH risk: it removes address-book entries that are absent from "
            "the CRM source. The preview lists every entry to be deleted before any "
            "deletion occurs."
        ),
    },
    {
        "principle": "Preserve Unrelated Fields",
        "description": (
            "Assigning an address book to a desktop profile changes only addressBookId. "
            "All other (non-deprecated) profile fields are read first and written back "
            "unchanged. Deprecated dial-plan fields are never sent."
        ),
    },
    {
        "principle": "Verify After You Write",
        "description": (
            "After committing, re-read the resource (list entries, or get the desktop "
            "profile) to confirm the change landed as expected."
        ),
    },
]

OPERATION_RISK_LEVELS: list[dict[str, Any]] = [
    {
        "risk": "HIGH",
        "operations": [
            "Delete an address book (tool_delete_address_book)",
            "Delete an entry (tool_delete_entry)",
            "Sync with pruning enabled (tool_sync_crm_to_address_book, prune=true)",
        ],
        "required_steps": [
            "Read current state",
            "Dry-run preview listing exactly what will be removed",
            "Explicit admin approval",
            "Commit one change (or one batch) at a time",
            "Verify by re-reading",
        ],
    },
    {
        "risk": "MEDIUM",
        "operations": [
            "Create/update an address book (tool_create_address_book / tool_update_address_book)",
            "Create/update an entry (tool_create_entry / tool_update_entry)",
            "Bulk-save entries (tool_bulk_save_entries)",
            "Sync without pruning (tool_sync_crm_to_address_book)",
            "Assign an address book to a profile (tool_assign_address_book_to_profile)",
        ],
        "required_steps": [
            "Dry-run preview",
            "Explicit admin approval",
            "Commit",
            "Verify by re-reading",
        ],
    },
]

ROLLBACK_PATTERNS: list[dict[str, str]] = [
    {
        "operation": "Assigned the wrong address book to a profile",
        "rollback": "Call tool_assign_address_book_to_profile with the original address book id",
    },
    {
        "operation": "Synced the wrong entries into a book",
        "rollback": "Update or delete affected entries; re-run sync from the correct CRM source",
    },
    {
        "operation": "Deleted an entry by mistake",
        "rollback": "Re-create it with tool_create_entry (or re-run sync without pruning)",
    },
]


def as_dict() -> dict[str, Any]:
    """Return the write-safety guide as a serializable dict."""
    return {
        "description": "Policies and patterns for safely executing WxCC write operations.",
        "safety_principles": SAFETY_PRINCIPLES,
        "operation_risk_levels": OPERATION_RISK_LEVELS,
        "rollback_patterns": ROLLBACK_PATTERNS,
    }
