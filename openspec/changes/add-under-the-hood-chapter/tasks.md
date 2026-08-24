## 1. Chapter scaffold and architecture map

- [x] 1.1 Add a new reference/self-study chapter after Chapter 9 (new "Chapter 10 — Under the
  hood: from tool call to authenticated REST call"), with an objective line and a `Reference:`
  list pointing at `api/`, `auth/oauth.py`, `config.py`, `errors.py`, `models/schemas.py`.
- [x] 1.2 Add the six-layer architecture diagram (client → server.py → _runtime → tools →
  models/schemas → api/client → auth/config/errors → WxCC), consistent with the layer names
  used elsewhere in the guide.
- [x] 1.3 Add a one-paragraph "how to read this chapter" note stating it is optional for the
  timed hands-on path and dual-purpose (operator reference + builder walkthrough).

## 2. The request path (down)

- [x] 2.1 Write the "one call, down the layers" section tracing `list_address_books`:
  `@mcp.tool` → `run_tool` → `tools/address_books.run_list` →
  `api/address_books.list_address_books` (path from `config.ADDRESS_BOOKS_PATH`) →
  `client.get`, naming each file/function.
- [x] 2.2 Explain `client.py._request`: bearer-header injection, family→base-URL selection,
  `429`/`5xx` retry with exponential backoff + jitter, `Retry-After` handling, and `2xx`→JSON.
- [x] 2.3 Add a short abridged snippet of `_request` (labelled "abridged") and a Builder callout
  on reusing this pattern for a new endpoint.

## 3. The failure path (up) and Chapter 9 anchor

- [x] 3.1 Write the failure-path section: `_raise_for_status` status→exception mapping
  (`404`/`403`/`429`/else), the `errors.py` typed hierarchy, and `translate_error` producing
  the token-free message.
- [x] 3.2 Add the C-vs-D contrast (E.164 rejected pre-network vs `403` after a real
  `wxcc_api_call`) and explicitly link each mapping to the matching Chapter 9 scenario-matrix
  row (do not duplicate the matrix).
- [x] 3.3 Add an Operator callout: "what each failure looks like in the log stream and which
  event proves the request reached WxCC."

## 4. Authentication and token security

- [x] 4.1 Write the auth section: `OAuthBroker.get_valid_token` acquire/refresh, expiry skew,
  and the `WXCC_ACCESS_TOKEN` PAT bypass the lab uses (skips the authorization-code flow).
- [x] 4.2 Document the token security invariants (per-session, Fernet-encrypted at rest,
  `0o600`, session isolation, never in tool output, never logged) and link to the redaction
  section (§8.3).
- [x] 4.3 Add a Builder callout on the encrypted per-session token store design and where the
  OAuth endpoints/scopes are configured (`config.py`, `# VERIFY`).

## 5. Configuration and typed contracts

- [x] 5.1 Write the config section: `Settings` from env/`.env`, `ApiFamily`/base URL, and the
  `# VERIFY` endpoint-path placeholders + go-live checklist pointer.
- [x] 5.2 Write the contracts section: `models/schemas.py` `*Input`/`*Output` and the E.164
  validator as the pre-network gate; show a bad-number rejection ties back to Chapter 3.

## 6. Operator troubleshooting map

- [x] 6.1 Add the "which file do I open when X breaks?" table mapping symptoms (retry storms,
  auth error with no `wxcc_api_call`, translated `403`, decrypt/`.env` issues) to the
  responsible file with a one-line reason.

## 7. Cross-links and verification

- [x] 7.1 Update the `Reference:` lines in Chapters 1, 3, 4, 7, and 9 to cross-link the new
  chapter; add a back-link from the new chapter to the Chapter 9 scenario matrix.
- [x] 7.2 Verify all cited symbols exist and match the source (`client.py._request`,
  `_raise_for_status`, `oauth.py.get_valid_token`, `config` path constants, schema names).
- [x] 7.3 Proof-read for consistent layer naming and confirm no source behavior was changed
  (docs-only, aside from any optional clarifying comments).
- [x] 7.4 Run `openspec validate add-under-the-hood-chapter --strict` and fix any issues.
