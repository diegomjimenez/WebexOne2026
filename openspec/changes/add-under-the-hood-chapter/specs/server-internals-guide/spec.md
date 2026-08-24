## ADDED Requirements

### Requirement: Guide teaches the request path from tool call to REST call

The lab guide SHALL include a reference/self-study chapter that traces a single concrete tool
call (`list_address_books`) down through the server layers, naming the file and function at
each layer, so a reader can navigate the source afterward. It SHALL show how `api/*.py` builds
a request path from a `config.py` endpoint constant, selects the API family/base URL, and
delegates to the shared `client.py` HTTP methods, and how `client.py._request` injects the
bearer token, retries `429`/`5xx` with backoff honoring `Retry-After`, and returns parsed JSON.

#### Scenario: Reader follows one call down the layers

- **WHEN** a reader works through the under-the-hood chapter for `list_address_books`
- **THEN** the chapter names, in order, `server.py` (the `@mcp.tool`), `_runtime.run_tool`,
  `tools/address_books.run_list`, `api/address_books.list_address_books` (path built from a
  `config.py` constant), and `api/client.py` (the authenticated `GET`)

#### Scenario: Reader learns the retry behavior

- **WHEN** the chapter explains `client.py._request`
- **THEN** it states that `429` and `5xx` are retried with exponential backoff plus jitter,
  that `Retry-After` is honored when present, and that a successful `2xx` returns parsed JSON

### Requirement: Guide teaches the failure/error-translation path and links it to troubleshooting

The guide SHALL explain how a non-2xx HTTP response becomes a plain-language message: the
status → typed-exception mapping in `client.py._raise_for_status` (`404`→`NotFoundError`,
`403`→`InsufficientPermissionsError`, `429`→`RateLimitError`, else `WxccApiError`), the typed
hierarchy in `errors.py`, and `translate_error` producing the token-free string the glass box
shows. It SHALL explicitly connect each mapping to the corresponding row of the existing
Chapter 9 scenario matrix rather than duplicating that matrix.

#### Scenario: Reader connects a 403 symptom to its mechanism

- **WHEN** a reader compares the Chapter 9 "permission denied (403)" row to the under-the-hood
  chapter
- **THEN** the chapter explains that the `wxcc_api_call` event is emitted before
  `_raise_for_status` maps the `403` to `InsufficientPermissionsError`, which `translate_error`
  renders as the plain-language permission message

#### Scenario: Reader distinguishes pre-network rejection from API refusal

- **WHEN** a reader reads the failure-path section
- **THEN** the chapter contrasts an E.164 validation error (rejected in the typed input model,
  no `wxcc_api_call`) with a `403` (a real `wxcc_api_call` that WxCC refuses), matching the
  Chapter 9 C-vs-D contrast

### Requirement: Guide teaches authentication and token security

The guide SHALL explain the `OAuthBroker` token lifecycle: acquiring and refreshing tokens,
the expiry skew, and the `WXCC_ACCESS_TOKEN` personal-access-token bypass the lab uses. It
SHALL state the security invariants that tokens are stored per session, encrypted at rest with
Fernet, never returned in tool output, and never written to logs (tying to the existing
redaction section).

#### Scenario: Reader understands the lab's token bypass

- **WHEN** a reader reaches the auth section
- **THEN** the chapter explains that setting `WXCC_ACCESS_TOKEN` makes `get_valid_token` return
  that token directly and skip the OAuth authorization-code flow, which is why the lab can run
  without a browser sign-in

#### Scenario: Reader learns the token security invariants

- **WHEN** the chapter describes token storage and handling
- **THEN** it states that tokens are per-session, Fernet-encrypted at rest, isolated so one
  session cannot read another's, and never appear in tool output or the log stream

### Requirement: Guide teaches configuration and typed contracts

The guide SHALL explain that `config.py` `Settings` loads configuration from the environment /
`.env`, that every external endpoint path is a `# VERIFY` placeholder to be confirmed before
go-live, and that the `models/schemas.py` typed `*Input`/`*Output` Pydantic models (including
the E.164 phone validator) form the contract that stops malformed writes before the network.

#### Scenario: Reader locates go-live placeholders

- **WHEN** a reader wants to take the server live
- **THEN** the chapter points at the `# VERIFY` / `# TODO` markers in `config.py` (base URL,
  OAuth endpoints, scopes, endpoint paths) and the go-live checklist

#### Scenario: Reader sees contracts as the pre-network gate

- **WHEN** the chapter explains `models/schemas.py`
- **THEN** it shows that a typed input model validates fields (e.g., E.164) before any API call,
  so invalid data is rejected with an actionable message rather than an opaque HTTP error

### Requirement: Guide provides an operator troubleshooting map and architecture diagram

The guide SHALL include a layered architecture diagram of the six server layers and a
"which file do I open when X breaks?" table mapping common failure symptoms to the responsible
source file, so the chapter doubles as an operator reference.

#### Scenario: Operator maps a symptom to a file

- **WHEN** an operator observes a specific failure (e.g., repeated `wxcc_api_retry`, an auth
  error with no `wxcc_api_call`, or a translated `403`)
- **THEN** the troubleshooting map directs them to the responsible file (`client.py`,
  `oauth.py`, or `errors.py`/`_common.py`) with a one-line reason

### Requirement: New chapter is cross-linked from existing chapters

The guide SHALL cross-link the under-the-hood chapter from the `Reference:` lines of the
chapters where the underlying layers are first felt (Chapters 1, 3, 4, 7, and 9), and the new
chapter SHALL link back to the Chapter 9 troubleshooting drill.

#### Scenario: Reader navigates from a hands-on chapter to the internals

- **WHEN** a reader is in Chapter 1, 3, 4, 7, or 9 and wants the underlying mechanism
- **THEN** a cross-link points them to the under-the-hood chapter, and that chapter links back
  to the Chapter 9 scenario matrix
