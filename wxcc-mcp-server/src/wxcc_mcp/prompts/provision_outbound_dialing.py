"""Prompt: provision_outbound_dialing.

Drives the full arc: find or create an address book, sync it from the CRM source,
choose a desktop profile (using the read tools), assign the book to that profile
on approval, and verify which agents gain access.
"""

from __future__ import annotations

PROMPT_NAME = "provision_outbound_dialing"
PROMPT_DESCRIPTION = (
    "End-to-end: build an address book from CRM data and provision it for agents by "
    "attaching it to a desktop profile, then verify which agents gain access."
)


def build_prompt(org_id: str, book_name: str = "", profile_id: str = "") -> str:
    """Build the end-to-end outbound-dialing provisioning prompt."""
    book_hint = (
        f'Preferred address book name: "{book_name}".'
        if book_name
        else "Ask the admin for the address book name (or reuse an existing one)."
    )
    profile_hint = (
        f'Target desktop profile: "{profile_id}".'
        if profile_id
        else "Use the read tools to help the admin choose which desktop profile to provision."
    )
    return f"""You are a Webex Contact Center (WxCC) administrator assistant.

TASK: Provision outbound dialing from CRM data for agents in org "{org_id}".
{book_hint}
{profile_hint}

Read the resources `crm://contacts`, `wxcc://reference/address-book-schema`, and
`wxcc://reference/write-safety-guide` first.

─── PHASE 1: ADDRESS BOOK ──────────────────────────────────────────────────
1. Call `tool_list_address_books`. If a suitable book exists, reuse it; otherwise
   call `tool_create_address_book` (name, parent_type) — preview, then commit on
   approval.

─── PHASE 2: SYNC FROM CRM (gated write) ───────────────────────────────────
2. Call `tool_sync_crm_to_address_book` for the chosen book WITHOUT approval to
   preview the diff; commit on explicit approval. Verify with `tool_list_entries`.

─── PHASE 3: CHOOSE A PROFILE (read-only) ──────────────────────────────────
3. Call `tool_map_profiles_to_agents` (or `tool_list_desktop_profiles` +
   `tool_list_agents`) to show each desktop profile, its current address book, and
   the agents assigned to it. Help the admin pick the target profile and note how
   many agents it affects.

─── PHASE 4: ASSIGN & VERIFY (gated write) ─────────────────────────────────
4. Call `tool_assign_address_book_to_profile` (profile_id, address_book_id) —
   preview shows current vs proposed addressBookId; commit on approval.
5. Call `tool_get_desktop_profile` to confirm the new address_book_id, and restate
   which agents now have access.

─── OUTPUT ─────────────────────────────────────────────────────────────────
Produce a final summary: the address book used, entries synced, the profile
assigned, and the list/count of agents who gained outbound-dial access.

Safety rules:
- NEVER commit a write without the admin's explicit approval.
- Assigning an address book changes only addressBookId; other profile settings
  are preserved.
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
            "name": "book_name",
            "description": "Preferred address book name (optional).",
            "required": False,
        },
        {
            "name": "profile_id",
            "description": "Target desktop profile id (optional — will help choose if omitted).",
            "required": False,
        },
    ]
