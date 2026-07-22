"""Prompt: sync_crm_to_address_book.

Drives the discover → sync → verify flow: read the CRM source, diff it against an
address book's existing entries, preview, sync on approval, and verify.
"""

from __future__ import annotations

PROMPT_NAME = "sync_crm_to_address_book"
PROMPT_DESCRIPTION = (
    "Synchronize CRM/directory contacts into a Webex Contact Center address book: "
    "discover, preview the diff, apply on approval, and verify."
)


def build_prompt(org_id: str, address_book_id: str = "", prune: bool = False) -> str:
    """Build the CRM→address-book sync walkthrough prompt."""
    book_hint = (
        f'Target address book: "{address_book_id}".'
        if address_book_id
        else "Ask the admin which address book to sync (use tool_list_address_books)."
    )
    prune_hint = (
        "Pruning is REQUESTED: entries absent from the CRM source will be deleted "
        "(HIGH risk — preview the deletions explicitly)."
        if prune
        else "Pruning is OFF: no entries will be deleted."
    )
    return f"""You are a Webex Contact Center (WxCC) administrator assistant.

TASK: Synchronize CRM contacts into an address book in org "{org_id}".
{book_hint}
{prune_hint}

Read the resources `crm://contacts`, `wxcc://reference/address-book-schema`, and
`wxcc://reference/write-safety-guide` first.

─── PHASE 1: DISCOVER (read-only) ──────────────────────────────────────────
1. Read `crm://contacts` — the source of truth for desired entries.
2. If no address book was given, call `tool_list_address_books` and confirm the target.
3. Call `tool_list_entries` for the target book to see the current state.

─── PHASE 2: PREVIEW & SYNC (gated write) ──────────────────────────────────
4. Call `tool_sync_crm_to_address_book` (org_id, address_book_id, prune) WITHOUT
   approval first — it returns a dry-run preview with counts to create, update,
   and delete. Show these counts to the admin.
5. Only on explicit approval, commit the sync. Watch progress stream per entry.

─── PHASE 3: VERIFY ────────────────────────────────────────────────────────
6. Call `tool_list_entries` again and confirm the entries match the CRM source.

─── OUTPUT ─────────────────────────────────────────────────────────────────
Produce a final summary: counts created/updated/deleted/skipped, the address
book id, and confirmation that the write-safety pattern was followed.

Safety rules:
- NEVER commit a write without the admin's explicit approval.
- NEVER enable pruning unless the admin explicitly asks; preview deletions first.
- If any step fails, STOP and report the error before continuing.
"""


def prompt_arguments() -> list[dict[str, object]]:
    """Return the prompt's declared argument metadata."""
    return [
        {
            "name": "org_id",
            "description": "Webex Contact Center organization id.",
            "required": True,
        },
        {
            "name": "address_book_id",
            "description": "Target address book id (optional — will ask if omitted).",
            "required": False,
        },
        {
            "name": "prune",
            "description": "Whether to delete entries absent from the CRM source (default false).",
            "required": False,
        },
    ]
