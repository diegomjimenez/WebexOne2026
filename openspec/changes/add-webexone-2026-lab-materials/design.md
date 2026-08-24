## Context

The 2025 session shipped a deck (`example_2025/presentation.pdf`, 69 slides) and a Lab Guide
(`example_2025/LabGuide.pdf`, 70 pages) backed by the `WebexOne2025/` code repo. The 2026
subject is the existing `wxcc-mcp-server` (agent lifecycle: onboard → diagnose → offboard),
taught in ~20–30 minutes. The mandated look is the `WebexOne 2026 - PowerPoint Light Template`
(`example_2025/WebexOne 2026 - PowerPoint Light Template_1782315244315001JnYv.pptx`) — a
59-slide Cisco-branded kit (Inter font; Cisco Blue / Midnight Blue / Medium Blue / White base;
magenta/orange accents) with layouts for title (2/4/6 speakers), contents, agenda, section
dividers, bulleted-with-subtitle content, big-number metrics, big statement, customer quote,
glass container, resources, and thank-you.

Content authority already lives in the repo: `wxcc-mcp-server/README.md`, `src/wxcc_mcp/tools/`,
`resources/`, and `prompts/`. So the materials are largely a *presentation layer* over facts
that already exist.

## Goals / Non-Goals

**Goals:**
- Reproduce the 2025 teaching rhythm (section-divided concept slides + lab checklists; step-by-step guide) for the WxCC MCP content.
- Produce the deck programmatically from the official template so it is diffable and regenerable.
- Keep slide/step content in an editable source decoupled from rendering code.
- Reference real `wxcc-mcp-server` modules; no new companion repo.

**Non-Goals:**
- No changes to `wxcc-mcp-server` runtime code, tests, or MCP surface.
- Not recreating the full multi-hour 2025 breadth; the session is intentionally short.
- Not designing a new brand/template — we consume the provided one as-is.
- Not resolving the server's `# VERIFY`/`# TODO` API placeholders (out of scope; the "Going further" track just points at them).

## Decisions

### D1: Generate the `.pptx` with python-pptx by cloning the template
Open the template with `python-pptx`, enumerate its slide layouts, and add new slides from the
matching layouts, populating placeholders. Theme (`theme1.xml`), fonts (embedded Inter), and
color scheme are inherited from the template automatically — the script sets text, never colors
or fonts.
- **Alternative — build by hand in PowerPoint**: fast once, but not diffable/reproducible; rejected per the chosen production method.
- **Alternative — Figma → export**: adds a design round-trip and export fidelity risk; rejected for a template-driven, text-heavy deck.
- **Approach for reuse**: prefer adding slides from the template's *layouts*; where a needed motif only exists as an example *slide* (e.g. big-number metrics), duplicate that slide's XML part via the packaging API and retext it.

### D2: Slide content lives in a structured source file
Author content as a single structured file (YAML or Python dict) keyed by track → slide → {layout, title, subtitle, bullets, reference, lab_steps, mode}. The generator maps `layout` names to template layout indices. This satisfies the "edit content without touching code" requirement and keeps the outline reviewable in isolation.

### D3: Layout-name → template-layout mapping table
A small mapping in the generator translates logical layout names (`title`, `contents`,
`section_divider`, `concept`, `metrics`, `statement`, `resources`, `thankyou`, `lab`) to the
concrete layout/example-slide in the template. `concept` (bulleted + subtitle, template slide 14)
is the workhorse; `lab` reuses `concept` with a checklist body and a hands-on/instructor badge.

### D4: Lab Guide authored in Markdown, distributed as PDF
Write the guide in Markdown (diffable, reviewable) under the lab-materials directory; the
distributed artifact is a PDF to match 2025. PDF conversion is a documented build step (e.g.
Pandoc), not hardcoded, so it stays tooling-agnostic.

### D5: New top-level `lab-materials/` directory
Keep all 2026 materials (generator, content source, output `.pptx`, guide `.md`/`.pdf`, its
README) in one directory, separate from `wxcc-mcp-server/`, reinforcing that python-pptx is
tooling-only and never a server runtime dependency.

## Risks / Trade-offs

- **python-pptx cannot fully clone every template motif (charts, SmartArt, complex groups)** → Restrict generated slides to text/bullet/number layouts; for rich decorative slides, duplicate the existing template slide part and only retext it, rather than rebuilding.
- **Embedded-font fidelity depends on the viewer having/embedding Inter** → Inherit the template's embedded fonts and avoid introducing new typefaces; verify no substitution warnings on open.
- **Content drift from the evolving `wxcc-mcp-server`** → Content source cites specific modules; a task verifies every cited path exists so drift surfaces at build/review time.
- **"Duplicate a slide part and retext it" is brittle if the template is re-versioned** → Pin to the provided template file; if the template changes, re-run the layout-mapping task first.
- **Scope creep back toward the 2025 multi-hour format** → Slide-count bound and the 2-hands-on/2-demo lab split are encoded in specs to hold the line.

## Open Questions

- Session title, session ID (template uses `BRKSEC-XXXX`), speaker names/titles, event date, and the QR/lab short-URLs — needed to fill the title, footer, and QR slides.
- Content-source format preference: YAML vs. a Python module (defaulting to YAML unless told otherwise).
- Is Pandoc an acceptable/available PDF toolchain for the Lab Guide, or is there a preferred converter?
