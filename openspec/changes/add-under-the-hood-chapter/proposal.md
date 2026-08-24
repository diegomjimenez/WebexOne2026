## Why

The lab guide teaches the top of the server — tools, resources, prompts, and the `run_tool`
orchestration — but stops before the layers an operator actually reaches for when
**troubleshooting or managing** a live WxCC integration: how a tool call becomes an
authenticated REST call (`api/` + `client.py`), how HTTP failures become the plain-language
messages the glass box shows (`errors.py` + `translate_error`), how tokens are brokered and
encrypted (`auth/oauth.py`), and where every external identifier is configured (`config.py`).
Chapter 9 already teaches the *symptoms* of this machinery ("a 403 produces a `wxcc_api_call`,
an E.164 error does not") without ever showing the code that *makes* that true. This change
closes that loop with a dedicated "under the hood" chapter — using code that already exists,
so it is a documentation change, not new behavior.

## What Changes

- **Add a new reference/self-study chapter — "Under the hood: from tool call to authenticated
  REST call"** — that follows one `list_address_books` call down all six layers and back up,
  serving both audiences: an admin sees *where failures come from and how to read them*, a
  developer sees *how to build/extend an authenticated API layer*.
- **Teach the request path** (`tools/ → api/*.py → client.py`): how `api/address_books.py`
  builds a path from a `config.py` constant, selects the API family/base URL, and calls
  `client.get/post/...`; and how the single `_request` method adds the bearer header, retries
  `429`/`5xx` with backoff + `Retry-After`, and returns parsed JSON.
- **Teach the failure path** (`client.py._raise_for_status → errors.py → translate_error`):
  the HTTP-status → typed-exception → plain-language mapping, explicitly connecting it to the
  Chapter 9 scenario matrix (404/403/429/network) so symptom and mechanism sit together.
- **Teach auth** (`auth/oauth.py`): the `OAuthBroker` acquire/refresh lifecycle, expiry skew,
  the **`WXCC_ACCESS_TOKEN` personal-access-token bypass** used by the lab, and per-session
  **Fernet token encryption at rest** — with the security invariant that tokens never reach the
  model or the logs.
- **Teach config & contracts** (`config.py`, `models/schemas.py`): `Settings` from env, the
  `# VERIFY` endpoint-path placeholders and go-live checklist, and how the typed `*Input`/
  `*Output` Pydantic models (incl. the E.164 validator) form the contract that stops bad writes
  before the network.
- **Add a layered architecture diagram** and a short "which file do I open when X breaks?"
  troubleshooting map so the chapter doubles as an operator reference.
- **Cross-link** the new chapter from existing `Reference:` lines (Ch. 1, 3, 4, 7, 9) so the
  layers are connected to the moments the learner already feels them.

Scope note: this is thread **A** of a larger guide-improvement effort (audience: both novice
admins and MCP developers; overall budget ~180 min). Prompts, elicitation-as-experience, and
the novice experience-first on-ramp are **out of scope here** and tracked as separate changes.
No source code behavior changes; edits are documentation plus optional teaching comments.

## Capabilities

### New Capabilities
- `server-internals-guide`: Requirements that the lab guide teach the server's request path,
  failure/error-translation path, auth/token brokering, and configuration/contract layers as a
  coherent "under the hood" chapter, grounded in the existing source, and usable as an operator
  troubleshooting reference.

### Modified Capabilities
<!-- No synced source-of-truth specs exist under openspec/specs/; prior lab-guide
     capabilities live only inside their originating changes. This change adds the new
     capability above and cross-links existing chapters; no existing requirement is altered. -->

## Impact

- **Docs:** `lab-materials/lab-guide/lab-guide.md` — one new chapter (placed after the current
  logging chapters as reference/self-study), a layered architecture diagram, a troubleshooting
  file-map, and updated `Reference:` cross-links in Chapters 1, 3, 4, 7, and 9.
- **Code (optional, non-behavioral):** at most a few clarifying teaching comments in
  `api/client.py` / `auth/oauth.py` if a referenced line needs an anchor; no logic changes.
- **Audience:** additive and layered — the new chapter is reference/self-study, so the hands-on
  20–30 min happy path (Ch. 1–6) is unchanged for time-boxed sessions.
- **Dependencies:** none. Uses existing code; introduces no new libraries.
