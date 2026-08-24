## Why

The `wxcc-mcp-server` has grown to ~100 tools, 13 prompts, and 13 resources across four
phases of WxCC coverage. That breadth actively works against the project's real end goal:
a **WebexOne hands-on lab** whose custom-MCP-server section is ~90 minutes shared across
three domains, leaving WxCC roughly **20–30 minutes**. The lab's purpose is to teach **MCP
server principles**, not WxCC completeness. A 100-tool manifest is impossible to teach in
that window, overwhelms learners, and even trips MCP clients that reject oversized tool
manifests. We need to slim the server down to a single, coherent teaching artifact.

## What Changes

- **Refocus the server on one narrative scenario — the "agent lifecycle"**: onboard an
  agent → diagnose "why can't this agent go Available?" → offboard the agent. This single
  story naturally exercises read, write, and diagnostic flows.
- **BREAKING: Delete the breadth.** Remove the Phase 2 (real-time/supervisory), Phase 3
  (full CRUD), and Phase 4 (advanced) tools, plus their API modules, schemas, prompts, and
  resources that are not part of the agent-lifecycle scenario. The lab repo will contain
  **only what is taught** (~12 tools, ~4 resources, ~2 prompts).
- **Add MCP depth so the lab touches every MCP primitive** (Thread D):
  - Upgrade the write-safety pattern from a `confirm=True` boolean into real **elicitation**
    (`ctx.elicit`) for onboard/offboard confirmation.
  - Emit **progress notifications** (`ctx.report_progress`) during multi-step onboarding.
  - Stream **client-facing logging** (`ctx.info/warning/error`) from tools.
  - Optionally demonstrate **sampling** (server asks the client's LLM to summarize a
    diagnosis) as a stretch goal.
- **Structure the artifact for "build-live + pre-built" delivery**: a minimal starter
  (one tool + one resource + one prompt) attendees build from scratch, plus the full
  diagnose/onboard/offboard implementation pre-built for them to run and read.
- **Update docs** (`README.md`) to describe the lab scenario, the MCP primitives it
  demonstrates, and the build-live vs. pre-built split. Remove references to deleted tools.

Out of scope for now: Webex Calling troubleshooting and multi-domain coverage (deferred).

## Capabilities

### New Capabilities
- `wxcc-lab-scenario`: The agent-lifecycle teaching scenario — the curated set of tools and
  prompts for onboard → diagnose → offboard, and the removal of all out-of-scenario breadth.
- `mcp-primitive-coverage`: Requirements that the lab server demonstrably exercises every
  MCP primitive (tools, resources, prompts, elicitation, progress, client-facing logging,
  and optional sampling), each tied to a concrete moment in the scenario.

### Modified Capabilities
<!-- openspec/specs/ is empty (no synced source-of-truth specs); no existing capability
     requirements change. The prior in-progress change `add-wxcc-availability-mcp` is
     superseded by this refactor and is addressed in Impact, not as a delta. -->

## Impact

- **Code (deletions):** `src/wxcc_mcp/tools/` (remove ~85 tools: all `manage_*` CRUD,
  real-time/supervisory, campaigns), matching `api/` modules (queues, skills, entry_points,
  sites, agent_profiles, multimedia_profiles, routing_strategies, business_hours,
  holiday_lists, flows, audio_files, webhooks, global_variables, outdial_ani, campaigns,
  realtime, search as applicable), `prompts/` (remove ~11), `resources/` (remove ~9),
  and the corresponding entries in `models/schemas.py` and `server.py`.
- **Code (additions/changes):** elicitation in the write tools; progress + ctx-logging in
  onboarding; optional sampling in diagnosis; simplification of `server.py` registration and
  the toolset-gating logic (likely removable once the manifest is small).
- **Docs:** `README.md` rewritten around the lab scenario and MCP-primitive coverage.
- **Relationship to prior work:** supersedes/absorbs the in-progress
  `add-wxcc-availability-mcp` direction, narrowing it to the lab artifact.
- **No new runtime dependencies.** OAuth broker, API client, config, logging, and error
  handling are retained (trimmed).
