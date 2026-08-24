# WebexOne 2026 — WxCC MCP Lab Materials

Presenter deck and attendee Lab Guide for the WebexOne 2026 session on the
**WxCC Agent Lifecycle MCP Server** (`../wxcc-mcp-server`). The materials reuse the
2025 teaching rhythm (section-divided concept slides + lab checklists; a step-by-step
guide) rendered in the official **WebexOne 2026 Light** PowerPoint template.

> These are build-time tools only. `python-pptx` is **not** a runtime dependency of
> `wxcc-mcp-server`.

## Layout

```
lab-materials/
  templates/webexone-2026-light.pptx     # official template (styling source of truth)
  content/deck.yaml                       # editable slide content (edit this, then rebuild)
  scripts/inspect_template.py             # enumerate template layouts/placeholders
  scripts/build_deck.py                   # generate the deck from template + content
  scripts/verify_deck.py                  # check theme/fonts/tracks/labs
  build/WebexOne2026-WxCC-MCP-Lab.pptx    # generated deck (output)
  lab-guide/lab-guide.md                  # attendee Lab Guide (source)
  TEMPLATE-ANALYSIS.md                    # layout mapping + rich-motif notes
```

## Setup (one time)

```powershell
cd lab-materials
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Build the deck

Edit `content/deck.yaml`, then regenerate (styling comes from the template — the
script only sets text):

```powershell
.\.venv\Scripts\python.exe scripts\build_deck.py
```

Output: `build/WebexOne2026-WxCC-MCP-Lab.pptx`. Regeneration is deterministic — the same
template + content yields the same slide set, order, and text.

Verify the result against the spec expectations (Inter fonts, 7 tracks, labelled labs):

```powershell
.\.venv\Scripts\python.exe scripts\verify_deck.py
```

Re-inspect the template's layouts/placeholders at any time:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_template.py
```

## Build the Lab Guide PDF

The guide is authored in Markdown (`lab-guide/lab-guide.md`) and distributed as PDF, matching
2025. Convert with Pandoc (or any Markdown→PDF tool):

```powershell
pandoc lab-guide\lab-guide.md -o build\WebexOne2026-WxCC-MCP-LabGuide.pdf
```

## Before delivery — fill the placeholders

`content/deck.yaml` `meta:` and a few slides contain values marked `PLACEHOLDER`:
session title, `session_id` (footer, e.g. `BRKCOL-1234`), speaker names/titles, event date,
and the QR/lab short-URLs on the "Join the conversation" and "Thank you" slides. Update them
and rebuild. QR code images are added in PowerPoint after generation.
