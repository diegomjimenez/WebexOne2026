# Template analysis — WebexOne 2026 Light

Generated aid for OpenSpec tasks 2.1–2.3. Source: `templates/webexone-2026-light.pptx`
(1 master, 49 layouts, 59 example slides, 16:9 @ 12192000×6858000 EMU).
Re-run `scripts/inspect_template.py` to refresh.

## Layout-name → logical-role mapping (task 2.2)

The generator (`scripts/build_deck.py`) uses these template layouts by name:

| Logical role   | Template layout                        | Placeholders used (idx) |
| -------------- | -------------------------------------- | ----------------------- |
| `title`        | `WebexOne 2026 Title Slide 1`          | 0=title, 13=subtitle, 11=speaker1, 14=speaker2, 12=date |
| `contents`     | `Agenda 1`                             | 0=title, 20=numbers (`##`), 18=list |
| `section`      | `Section, Title Only 1`                | 0=number, 12=section title |
| `concept`      | `Title, 1 Column with Bullets`         | 0=title, 12=bullet body |
| `lab`          | `Title, 1 Column with Bullets`         | 0=title (with badge), 12=checklist body |
| `statement`    | `Statement 1, Title, Subtitle`         | 0=title, 11=subtitle |
| `resources`    | `1/2 Slide, Title, Body Copy, Graphic 1` | 0=title, 11=body |
| `thankyou`     | `Thank you`                            | 0=title |

All layouts also carry a `FOOTER` placeholder inheriting `Session ID: BRKSEC-XXXX`
and a `SLIDE_NUMBER` placeholder; new slides inherit these automatically. The footer
is overridden per-deck only when `meta.session_id` is set in the content source.

## Rich motifs requiring duplicate-and-retext (task 2.3)

The **big-number metrics** motif (template example slides 32–34, "Growth metrics") is
NOT placeholder-driven — each figure (e.g. `218%`) and its caption is a hand-placed
text box. python-pptx cannot populate these via layout placeholders.

Approach: `duplicate_slide(prs, source_index)` deep-copies an existing example slide's
XML part, then `retext_by_map()` replaces known source strings with our values. This is
deterministic against the pinned template. Example slide 33 ("Growth metrics", layout
`1/2 Slide Title 1`) is the clone source for the "curated surface" numbers slide
(16 tools · 6 resources · 2 prompts · 7 primitives).

Fallback: if a maintainer would rather avoid the clone, the same slide can be authored
as a `concept` slide — the content source supports either.
