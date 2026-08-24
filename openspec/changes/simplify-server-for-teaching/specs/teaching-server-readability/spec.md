## ADDED Requirements

### Requirement: Cross-cutting runtime is quarantined from the entrypoint

The MCP server SHALL keep cross-cutting runtime machinery (per-session client/session
resolution, correlation-id generation, timing, result summarization, the run-orchestration
helper, and the elicitation/progress/sampling helpers) in a dedicated module separate from
`server.py`. `server.py` SHALL import these helpers rather than define them.

#### Scenario: Runtime helpers live in a separate module

- **WHEN** the source tree is inspected
- **THEN** a module `wxcc_mcp/_runtime.py` defines `run_tool`, `should_commit`, `emit_progress`,
  `maybe_summarize`, `get_client`, and `session_id`
- **AND** `server.py` imports them from `._runtime` and does not redefine them

#### Scenario: Entrypoint reads as tools plus wiring

- **WHEN** `server.py` is read top to bottom
- **THEN** its ordering is imports → tool definitions (with anatomy banners) → resources →
  prompts → `main()`
- **AND** the cross-cutting helpers are not interleaved between tool definitions

### Requirement: Behavior is unchanged by the refactor

The refactor SHALL be behavior-preserving. Tool signatures, tool names, MCP primitives
(elicitation, progress, sampling), error translation, and structured logging SHALL be identical
to before the change.

#### Scenario: Existing tests pass

- **WHEN** the test suite is run after the refactor
- **THEN** the logging/orchestration tests pass with the same assertions on structured events
  and correlation behavior (adjusted only for the new import locations/names)

#### Scenario: Tool surface is unchanged

- **WHEN** the registered MCP tools are enumerated
- **THEN** the same tool names and signatures are present as before the refactor

### Requirement: One annotated tool exemplar explains the pattern once

`server.py` SHALL include a concise "anatomy of an MCP tool" annotation above the first read
tool and the first write tool that explains the shared 3-move shape and the deferred-execution
`lambda:` idiom exactly once, without repeating per-tool commentary.

#### Scenario: Read and write exemplars are annotated

- **WHEN** a participant opens `server.py`
- **THEN** an anatomy banner precedes `tool_list_address_books` explaining resolve-client →
  map-args-and-call → hand to `run_tool`, including why the call is wrapped in `lambda:`
- **AND** an anatomy banner precedes `tool_create_address_book` explaining the `should_commit`
  write gate
- **AND** the remaining tools are left free of redundant boilerplate comments

### Requirement: Lab guide teaches the server via progressive disclosure

The lab guide SHALL introduce the server with a three-level progression: a minimal explicit tool
(how MCP works), the resulting repetition problem, and the extracted `run_tool` pattern (how the
server is built), pointing readers to `_runtime.py`.

#### Scenario: Chapter 1 presents the anatomy progression

- **WHEN** a participant reads Chapter 1
- **THEN** they first see a short, helper-free MCP tool illustrating the bare round-trip
- **AND** they then read why real tools need logging, error translation, and a write gate
- **AND** they are pointed to `run_tool` / `_runtime.py` as the factored-out pattern

#### Scenario: Production DRY option is narrative only

- **WHEN** the guide mentions a `@wxcc_tool`-style decorator as the production way to remove
  boilerplate
- **THEN** it is presented as prose/example only
- **AND** the running lab code does not add such a decorator, keeping tools explicit on purpose
