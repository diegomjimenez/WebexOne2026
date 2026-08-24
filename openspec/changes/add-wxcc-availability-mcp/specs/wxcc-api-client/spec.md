## ADDED Requirements

### Requirement: Async client with bearer injection

The API client SHALL wrap `httpx.AsyncClient` and inject the bearer token obtained from the auth broker on every outbound request. Callers SHALL NOT pass tokens directly; the client resolves them per session.

#### Scenario: Bearer token attached to each request

- **WHEN** the client issues any request on behalf of a session
- **THEN** the request includes an `Authorization: Bearer <token>` header resolved from the auth broker for that session

### Requirement: Distinct base URLs for Config and Reporting/Search families

The client SHALL treat the Config API and the Reporting/Search API as separate families, each with its own base URL defined as a named configuration constant. Endpoint paths SHALL be defined as named constants annotated for verification against developer.webex.com.

#### Scenario: Correct base URL selected per family

- **WHEN** a Config API tool and a Reporting/Search API tool each make a request
- **THEN** each request targets its family's configured base URL and named path constant

### Requirement: Retry with backoff and Retry-After handling

The client SHALL retry `429` and `5xx` responses using exponential backoff, and SHALL honor the `Retry-After` header when present. Non-retryable responses SHALL NOT be retried.

#### Scenario: Rate-limited request is retried after delay

- **WHEN** a request returns HTTP 429 with a `Retry-After` header
- **THEN** the client waits at least the indicated interval and retries the request

#### Scenario: Server error is retried with backoff

- **WHEN** a request returns HTTP 503 without a `Retry-After` header
- **THEN** the client retries using exponential backoff up to the configured maximum attempts

#### Scenario: Client error is not retried

- **WHEN** a request returns HTTP 404
- **THEN** the client does not retry and surfaces the mapped error immediately

### Requirement: Typed exception mapping for non-2xx responses

The client SHALL map non-2xx responses to typed exceptions: `NotFoundError` (404), `InsufficientPermissionsError` (403), `RateLimitError` (429 after retries exhausted), and `WxccApiError` (other non-2xx). Exceptions SHALL carry enough context for tools to produce plain-language messages without leaking token material.

#### Scenario: 404 maps to NotFoundError

- **WHEN** a request returns HTTP 404
- **THEN** the client raises `NotFoundError`

#### Scenario: Exhausted retries map to RateLimitError

- **WHEN** a request returns HTTP 429 on every attempt up to the retry limit
- **THEN** the client raises `RateLimitError` after the final attempt

#### Scenario: Unexpected status maps to WxccApiError

- **WHEN** a request returns an unmapped non-2xx status (e.g., HTTP 400)
- **THEN** the client raises `WxccApiError` carrying the status and safe context
