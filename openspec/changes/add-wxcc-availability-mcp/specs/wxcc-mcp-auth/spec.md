## ADDED Requirements

### Requirement: Per-session OAuth token brokerage

The server SHALL implement an OAuth 2.0 Authorization Code flow against the Webex/WxCC identity provider and broker access tokens on behalf of each session. The server SHALL expose `get_valid_token(session_id)` returning a live access token. Tokens SHALL NOT be hardcoded, and the IdP authorization/token endpoints and scopes SHALL be sourced from configuration placeholders marked for verification against developer.webex.com (never invented inline).

#### Scenario: Valid token returned for authenticated session

- **WHEN** `get_valid_token(session_id)` is called for a session with a stored, unexpired token
- **THEN** the broker returns the live access token without contacting the IdP

#### Scenario: Missing authorization surfaces a typed error

- **WHEN** `get_valid_token(session_id)` is called for a session with no stored token
- **THEN** the broker raises a typed authentication error indicating the session must complete the OAuth flow

### Requirement: Automatic token refresh

The broker SHALL detect expired (or near-expiry) access tokens and refresh them using the stored refresh token before returning a token to a caller, without requiring model or user intervention.

#### Scenario: Expired token is refreshed transparently

- **WHEN** `get_valid_token(session_id)` is called and the stored access token is expired but the refresh token is valid
- **THEN** the broker obtains a new access token via the refresh grant and returns the refreshed token

#### Scenario: Refresh failure surfaces a typed error

- **WHEN** the refresh grant fails (e.g., refresh token revoked or expired)
- **THEN** the broker raises a typed authentication error and does not return a stale or empty token

### Requirement: Per-session token isolation and encrypted storage

The broker SHALL store tokens per session, encrypted at rest, such that one session's token can never be read by or leaked into another session. Tokens SHALL NEVER be exposed to the model nor returned in any tool output.

#### Scenario: Sessions cannot access each other's tokens

- **WHEN** session A and session B both hold brokered tokens
- **THEN** a `get_valid_token` call scoped to session A never returns session B's token

#### Scenario: Tokens are absent from tool outputs

- **WHEN** any tool completes and returns its structured result
- **THEN** the result contains no access token, refresh token, or raw Authorization header value

### Requirement: Token scope coverage for both API families

Brokered tokens SHALL carry scopes sufficient for BOTH the Config API reads AND the Reporting/Search API reads required by the diagnostic tools. Scope identifiers SHALL be defined as verifiable configuration placeholders.

#### Scenario: Token authorizes both API families

- **WHEN** a diagnostic workflow calls both a Config API tool and a Reporting/Search API tool within one session
- **THEN** the same brokered token is accepted by both API families without a second authorization

### Requirement: Insufficient-permission mapping

When the identity or an API returns a `403`, the broker/client layer SHALL raise a typed `InsufficientPermissionsError` that tools translate into a plain-language statement of what the caller lacks rights to do.

#### Scenario: 403 becomes a plain-language message

- **WHEN** an API call returns HTTP 403 for the current session
- **THEN** a typed `InsufficientPermissionsError` is raised and the invoking tool returns a plain-language explanation of the missing permission (with no token material)
