## 1. Scaffold lab-materials workspace

- [x] 1.1 Create top-level `lab-materials/` directory with a `README.md` documenting build commands
- [x] 1.2 Add `python-pptx` (and PDF toolchain, e.g. Pandoc) as tooling-only dependencies with pinned versions, isolated from `wxcc-mcp-server`
- [x] 1.3 Copy/reference the official template into `lab-materials/templates/` and confirm it opens with python-pptx

## 2. Analyze the template

- [x] 2.1 Enumerate the template's slide layouts and placeholder indices; record them
- [x] 2.2 Build the layout-name → template-layout mapping table (title, contents, section_divider, concept, metrics, statement, resources, thankyou, lab)
- [x] 2.3 Identify motifs only available as example slides (e.g. big-number metrics) and confirm the duplicate-part-and-retext approach works for them

## 3. Author the content source

- [x] 3.1 Define the structured content-source schema (track → slide → {layout, title, subtitle, bullets, reference, lab_steps, mode})
- [x] 3.2 Write the deck content for the 7 tracks (~19 slides) per the agreed outline, marking hands-on vs instructor-run labs
- [x] 3.3 Fill title/footer/QR placeholders (session title, session ID, speakers, date, lab short-URLs) — wired with clearly-marked `PLACEHOLDER` values pending real event details (see README + deck.yaml `meta`)
- [x] 3.4 Verify every cited `wxcc-mcp-server` module path in the content actually exists

## 4. Build the deck generator

- [x] 4.1 Implement the generator: open template, read content source, add slides from mapped layouts, populate placeholders (text only — no colors/fonts set in code)
- [x] 4.2 Implement the duplicate-slide-part-and-retext helper for rich motifs
- [x] 4.3 Emit the `.pptx` and make regeneration deterministic (stable ordering/content)
- [x] 4.4 Add the documented single build command to `lab-materials/README.md`

## 5. Author the Lab Guide

- [x] 5.1 Write "About this lab" + objectives (onboard → diagnose → offboard, MCP primitives)
- [x] 5.2 Write "Getting started" using the real setup (Python 3.11+, venv, `pip install -e ".[dev]"`, `WXCC_TOKEN_ENCRYPTION_KEY`, `.env`, connect MCP client)
- [x] 5.3 Write the Build-live chapter (write `tool_get_user` + a resource + the diagnose prompt) with numbered steps and a Solution callout
- [x] 5.4 Write the Diagnose chapter (run the prompt; read `validate_agent_routing` evidence) with a Solution callout
- [x] 5.5 Write the Onboard/offboard chapter (`tool_onboard_agent`: elicitation, progress, dry-run fallback) with a Solution callout
- [x] 5.6 Write the "Going further" chapter (sampling, `WXCC_LOG_FILE`, resolving `# VERIFY`/`# TODO`)
- [x] 5.7 Add the documented Markdown → PDF build step

## 6. Verify against specs

- [x] 6.1 Confirm the deck renders with template theme/Inter and no missing-font warnings; slide count within target
- [x] 6.2 Confirm the seven tracks, dividers, concept-slide reference links, and lab badges are present
- [x] 6.3 Confirm the Lab Guide getting-started references resolve (`.env.example`, `[dev]` extra, `wxcc-mcp-server` console script, `WXCC_TOKEN_ENCRYPTION_KEY` all present in the repo)
- [x] 6.4 Confirm `wxcc-mcp-server` package + tests do not import or require python-pptx
