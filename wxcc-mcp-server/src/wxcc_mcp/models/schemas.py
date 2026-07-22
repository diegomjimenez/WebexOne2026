"""Pydantic models for every tool's inputs and outputs.

These models are the typed contract between the MCP tools and the model. They
double as JSON schema sources for MCP and as fixtures for tests. No model here
carries token material — tokens never appear in tool inputs or outputs.

Scope: this lab server implements a single scenario — synchronizing CRM contacts
into a Webex Contact Center **Address Book** and provisioning it for agents by
attaching it to a **Desktop Profile**. All models pertain to that scenario and
live in the WxCC Config API family.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Shared / common models + validation
# ---------------------------------------------------------------------------

# E.164: a leading '+' followed by up to 15 digits, first digit non-zero.
_E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")


def normalize_e164(value: str) -> str:
    """Normalize and validate an E.164 phone number.

    Strips spaces, hyphens, and parentheses, then enforces the E.164 shape via
    an allow-list regex. Raises ``ValueError`` on anything that is not valid
    E.164 so invalid input is rejected before any API call.
    """
    cleaned = re.sub(r"[\s\-()]", "", value or "")
    if not _E164_RE.match(cleaned):
        raise ValueError(f"Phone number {value!r} is not valid E.164 (e.g. +14155551234).")
    return cleaned


class OrgScopedInput(BaseModel):
    """Base for inputs that operate within an organization."""

    org_id: str = Field(..., description="Webex Contact Center organization id.")


class WriteInput(OrgScopedInput):
    """Base for write inputs.

    ``confirm`` remains as a fallback for MCP clients that do not support
    elicitation. When elicitation IS available, the tool asks the user to
    approve interactively regardless of this flag.
    """

    confirm: bool = Field(
        default=False,
        description="Fallback commit flag for clients without elicitation support.",
    )


class WriteOutput(BaseModel):
    """Result of a write tool: either a dry-run preview or a committed change."""

    committed: bool = False
    dry_run: bool = True
    resource_id: str | None = None
    message: str | None = None
    preview: dict | None = None
    result: dict | None = None


# ---------------------------------------------------------------------------
# Address Books
# ---------------------------------------------------------------------------


class AddressBookItem(BaseModel):
    """An address book summary."""

    address_book_id: str = Field(..., description="Address book id.")
    name: str | None = Field(default=None, description="Address book name.")
    description: str | None = Field(default=None, description="Address book description.")
    parent_type: str | None = Field(
        default=None, description="Availability scope: e.g. CUSTOMER (org-wide) or SITE."
    )


class ListAddressBooksInput(OrgScopedInput):
    """Input for ``list_address_books``."""

    max_results: int = Field(
        default=100, ge=1, le=100, description="Maximum address books to return (API cap 100)."
    )


class ListAddressBooksOutput(BaseModel):
    """Output for ``list_address_books``."""

    org_id: str
    total_returned: int
    address_books: list[AddressBookItem] = Field(default_factory=list)


class GetAddressBookInput(OrgScopedInput):
    """Input for ``get_address_book``."""

    address_book_id: str = Field(..., description="Address book id.")


class CreateAddressBookInput(WriteInput):
    """Input for ``create_address_book``."""

    name: str = Field(..., description="Address book name (required).")
    parent_type: str = Field(
        ..., description="Availability scope (required): e.g. CUSTOMER or SITE."
    )
    description: str | None = Field(default=None, description="Optional description.")


class UpdateAddressBookInput(WriteInput):
    """Input for ``update_address_book``."""

    address_book_id: str = Field(..., description="Address book id to update.")
    name: str | None = Field(default=None, description="Updated name.")
    description: str | None = Field(default=None, description="Updated description.")


class DeleteAddressBookInput(WriteInput):
    """Input for ``delete_address_book``."""

    address_book_id: str = Field(..., description="Address book id to delete.")


# ---------------------------------------------------------------------------
# Address Book Entries
# ---------------------------------------------------------------------------


class EntryItem(BaseModel):
    """An address book entry (a dialable contact)."""

    entry_id: str = Field(default="", description="Entry id.")
    name: str | None = Field(default=None, description="Contact name.")
    number: str | None = Field(default=None, description="Phone number (E.164).")
    crm_id: str | None = Field(
        default=None, description="Originating CRM id, if stored as an attribute."
    )


class ListEntriesInput(OrgScopedInput):
    """Input for ``list_entries``."""

    address_book_id: str = Field(..., description="Address book id.")
    search: str | None = Field(default=None, description="Search keyword.")
    filter: str | None = Field(default=None, description="RSQL filter expression.")
    attributes: str | None = Field(
        default=None, description="Comma-separated attributes to return (id,name,number)."
    )
    page: int = Field(default=0, ge=0, description="Page number (starts at 0).")
    page_size: int = Field(default=100, ge=1, le=100, description="Items per page (cap 100).")


class ListEntriesOutput(BaseModel):
    """Output for ``list_entries``."""

    org_id: str
    address_book_id: str
    total_returned: int
    entries: list[EntryItem] = Field(default_factory=list)


class GetEntryInput(OrgScopedInput):
    """Input for ``get_entry``."""

    address_book_id: str = Field(..., description="Address book id.")
    entry_id: str = Field(..., description="Entry id.")


class CreateEntryInput(WriteInput):
    """Input for ``create_entry``."""

    address_book_id: str = Field(..., description="Address book id.")
    name: str = Field(..., description="Contact name (required).")
    number: str = Field(..., description="Phone number in E.164 (required).")
    crm_id: str | None = Field(default=None, description="Optional originating CRM id.")

    @field_validator("number")
    @classmethod
    def _validate_number(cls, value: str) -> str:
        return normalize_e164(value)


class UpdateEntryInput(WriteInput):
    """Input for ``update_entry``."""

    address_book_id: str = Field(..., description="Address book id.")
    entry_id: str = Field(..., description="Entry id to update.")
    name: str | None = Field(default=None, description="Updated name.")
    number: str | None = Field(default=None, description="Updated phone number (E.164).")

    @field_validator("number")
    @classmethod
    def _validate_number(cls, value: str | None) -> str | None:
        return normalize_e164(value) if value is not None else None


class DeleteEntryInput(WriteInput):
    """Input for ``delete_entry``."""

    address_book_id: str = Field(..., description="Address book id.")
    entry_id: str = Field(..., description="Entry id to delete.")


class EntryInput(BaseModel):
    """A single entry payload used by bulk save and sync."""

    name: str = Field(..., description="Contact name.")
    number: str = Field(..., description="Phone number in E.164.")
    crm_id: str | None = Field(default=None, description="Optional originating CRM id.")

    @field_validator("number")
    @classmethod
    def _validate_number(cls, value: str) -> str:
        return normalize_e164(value)


class BulkSaveEntriesInput(WriteInput):
    """Input for ``bulk_save_entries``."""

    address_book_id: str = Field(..., description="Address book id.")
    entries: list[EntryInput] = Field(
        default_factory=list, description="Entries to create or upsert in bulk."
    )


# ---------------------------------------------------------------------------
# Desktop Profiles
# ---------------------------------------------------------------------------


class DesktopProfileItem(BaseModel):
    """A desktop profile summary (deprecated dial-plan fields intentionally omitted)."""

    profile_id: str = Field(..., description="Desktop profile id.")
    name: str | None = Field(default=None, description="Desktop profile name.")
    address_book_id: str | None = Field(
        default=None, description="Currently assigned address book id, if any."
    )


class ListDesktopProfilesInput(OrgScopedInput):
    """Input for ``list_desktop_profiles``."""

    max_results: int = Field(default=100, ge=1, le=100, description="Max profiles (cap 100).")


class ListDesktopProfilesOutput(BaseModel):
    """Output for ``list_desktop_profiles``."""

    org_id: str
    total_returned: int
    profiles: list[DesktopProfileItem] = Field(default_factory=list)


class GetDesktopProfileInput(OrgScopedInput):
    """Input for ``get_desktop_profile``."""

    profile_id: str = Field(..., description="Desktop profile id.")


class AssignAddressBookInput(WriteInput):
    """Input for ``assign_address_book_to_profile``."""

    profile_id: str = Field(..., description="Desktop profile id to update.")
    address_book_id: str = Field(..., description="Address book id to assign.")


# ---------------------------------------------------------------------------
# Agents (read-only discovery)
# ---------------------------------------------------------------------------


class AgentSummary(BaseModel):
    """A brief summary of one agent/user with its desktop profile assignment."""

    user_id: str
    email: str | None = None
    display_name: str | None = None
    desktop_profile_id: str | None = Field(
        default=None, description="Assigned desktop profile id, if any."
    )


class ListAgentsInput(OrgScopedInput):
    """Input for ``list_agents``."""

    max_results: int = Field(default=100, ge=1, le=100, description="Max agents (cap 100).")


class ListAgentsOutput(BaseModel):
    """Output for ``list_agents``."""

    org_id: str
    total_returned: int
    agents: list[AgentSummary] = Field(default_factory=list)


class GetAgentInput(OrgScopedInput):
    """Input for ``get_agent``."""

    identifier: str = Field(..., description="Agent (user) id.")


class ProfileAgentMapInput(OrgScopedInput):
    """Input for ``map_profiles_to_agents``."""

    max_results: int = Field(default=100, ge=1, le=100)


class ProfileAgentMapping(BaseModel):
    """The agents assigned to a single desktop profile."""

    profile_id: str
    profile_name: str | None = None
    address_book_id: str | None = None
    agents: list[AgentSummary] = Field(default_factory=list)


class ProfileAgentMapOutput(BaseModel):
    """Output for ``map_profiles_to_agents``."""

    org_id: str
    mappings: list[ProfileAgentMapping] = Field(default_factory=list)
    unassigned_agents: list[AgentSummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# CRM source + composite sync
# ---------------------------------------------------------------------------


class CrmContact(BaseModel):
    """A contact record from the CRM source resource."""

    id: str = Field(..., description="Stable CRM contact id.")
    name: str = Field(..., description="Contact name.")
    number: str = Field(..., description="Phone number (E.164).")

    @field_validator("number")
    @classmethod
    def _validate_number(cls, value: str) -> str:
        return normalize_e164(value)


class SyncCrmInput(WriteInput):
    """Input for ``sync_crm_to_address_book``."""

    address_book_id: str = Field(..., description="Target address book id.")
    prune: bool = Field(
        default=False,
        description="If true, delete existing entries not present in the CRM source (HIGH risk).",
    )
    summarize: bool = Field(
        default=False, description="Ask the client model to summarize the result (sampling)."
    )


class SyncAction(BaseModel):
    """A single planned or applied sync action."""

    action: str = Field(..., description="One of: create, update, delete, skip.")
    name: str | None = None
    number: str | None = None
    entry_id: str | None = None
    crm_id: str | None = None
    reason: str | None = None


class SyncOutput(BaseModel):
    """Output for ``sync_crm_to_address_book``."""

    address_book_id: str
    committed: bool = False
    dry_run: bool = True
    to_create: int = 0
    to_update: int = 0
    to_delete: int = 0
    skipped: int = 0
    actions: list[SyncAction] = Field(default_factory=list)
    message: str | None = None
    llm_summary: str | None = None
