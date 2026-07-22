## ADDED Requirements

### Requirement: Deck adopts the WebexOne 2026 Light template branding

The deck SHALL use the theme, color palette, and typography of the official
`WebexOne 2026 - PowerPoint Light Template` (Inter font family; Cisco Blue / Midnight Blue /
Medium Blue / White base palette; magenta and orange accents). No off-template colors or fonts
SHALL be introduced.

#### Scenario: Slides render with template theme

- **WHEN** the generated deck is opened in PowerPoint
- **THEN** every slide uses the template's theme colors and the Inter typeface with no
  missing-font substitution warnings

#### Scenario: Content reuses provided layouts

- **WHEN** a slide is created for a given purpose (title, contents, section divider, bulleted
  content, big-number metrics, big statement, resources, thank-you)
- **THEN** it is built on the corresponding layout from the template rather than a blank slide

### Requirement: Deck follows the 2025 teaching rhythm across seven tracks

The deck SHALL open with a "join the conversation" slide, a title slide, and a contents slide,
then present seven tracks — (01) Why MCP + WxCC, (02) MCP primitives, (03) Setup & connect,
(04) Build-live, (05) Diagnose, (06) Onboard/offboard + write-safety, (07) Going further —
each introduced by a section divider, and SHALL close with a resources slide and a
thank-you/survey slide.

#### Scenario: Track ordering and dividers

- **WHEN** the deck is reviewed end to end
- **THEN** the seven tracks appear in the specified order, each preceded by a section-divider
  slide numbered 01–07

#### Scenario: Concept slides carry a reference link

- **WHEN** a concept slide explains an MCP or WxCC topic
- **THEN** it presents a short title, 3–6 bullets, and a reference URL (e.g.
  `modelcontextprotocol.io` or `developer.webex.com`) in the 2025 style

### Requirement: Deck marks hands-on labs and instructor demos

The deck SHALL include lab-activity checklist slides that distinguish the two hands-on labs
(setup + build-live; run the onboard/offboard write flow) from the two instructor-run demos
(the `validate_agent_routing` diagnose flow; sampling / real-API notes).

#### Scenario: Lab activity slide format

- **WHEN** a track that includes a lab is presented
- **THEN** a lab-activity slide lists numbered steps and clearly indicates whether it is
  hands-on or instructor-run

### Requirement: Deck scope fits a 20–30 minute session

The deck SHALL be sized (~19 content slides) to be delivered in approximately 20–30 minutes,
matching the `wxcc-mcp-server` stated teaching scope.

#### Scenario: Slide count bounded

- **WHEN** the deck is generated
- **THEN** its total slide count stays within the agreed target and does not reintroduce the
  full multi-hour 2025 breadth
