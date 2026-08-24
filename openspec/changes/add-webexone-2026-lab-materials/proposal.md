## Why

The 2025 WebexOne session ("Exploring the Possibilities of Webex APIs") shipped as a paired
deck + step-by-step Lab Guide, and that format worked well. For 2026 the subject is the
`wxcc-mcp-server` — a WxCC Agent Lifecycle MCP server taught through the narrative
**onboard → diagnose → offboard**. We need matching presenter and attendee materials that
reuse the proven 2025 teaching rhythm but adopt the mandated **WebexOne 2026 Light**
PowerPoint template and fit the server's stated ~20–30 minute scope.

## What Changes

- Add a **presentation deck** (~19 slides) built by cloning the theme, fonts, and layouts of
  `example_2025/WebexOne 2026 - PowerPoint Light Template_1782315244315001JnYv.pptx`, following
  the 2025 rhythm: title → contents → 7 section-divided tracks of concept slides
  (bullets + reference link) punctuated by lab-activity checklists → resources → thank-you/survey.
- Add a **step-by-step Lab Guide** document mirroring the deck's tracks in the 2025 style
  (objectives → numbered `Step X.Y` instructions → Solution callouts), referencing the existing
  `wxcc-mcp-server/` modules instead of a new companion repo.
- Add a **reproducible generation pipeline** (python-pptx) that emits the `.pptx` from the
  template so the deck is diffable and regenerable rather than hand-built.
- Track structure confirmed: 01 Why MCP+WxCC · 02 Primitives · 03 Setup & connect ·
  04 Build-live · 05 Diagnose · 06 Onboard/offboard + write-safety · 07 Going further, with
  2 hands-on labs and 2 instructor-run demos.

## Capabilities

### New Capabilities
- `lab-presentation-deck`: A WebexOne 2026 slide deck, generated from the official Light template,
  that presents the WxCC MCP agent-lifecycle content in the 2025 teaching rhythm.
- `lab-guide-document`: A step-by-step attendee Lab Guide that walks through setup, build-live,
  diagnose, and onboard/offboard using the existing `wxcc-mcp-server` codebase.
- `deck-generation-pipeline`: A python-pptx-based build that reproducibly clones the template's
  theme/layouts and populates slides from a structured outline.

### Modified Capabilities
<!-- None: this change adds lab materials and a build pipeline; it does not alter existing wxcc-mcp-server requirements. -->

## Impact

- **New files**: a generation script + slide-content source under a new `lab-materials/`
  (or similar) directory, the produced `.pptx`, and a Lab Guide (Markdown, with PDF as the
  distributed form to match 2025).
- **New dependency**: `python-pptx` (build-time/tooling only; not a runtime dependency of the server).
- **Inputs consumed**: the 2026 template `.pptx` and the existing `wxcc-mcp-server/` source
  (tools, resources, prompts, README) as the authoritative content source.
- **No changes** to the `wxcc-mcp-server` runtime code, its tests, or its public MCP surface.
