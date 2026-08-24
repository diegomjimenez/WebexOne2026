## ADDED Requirements

### Requirement: Deck is generated reproducibly from the template

The pipeline SHALL produce the `.pptx` deck programmatically with python-pptx by opening the
official 2026 template and populating slides from its layouts, so that regenerating from the
same inputs yields an equivalent deck.

#### Scenario: Regeneration is deterministic

- **WHEN** the generation script is run twice against the same template and content source
- **THEN** it produces decks with the same slide set, ordering, and text content

#### Scenario: Template is the styling source of truth

- **WHEN** the script builds a slide
- **THEN** it derives theme, fonts, and layouts from the template file rather than hardcoding
  colors or font names in the script

### Requirement: Slide content is defined in a structured, editable source

The pipeline SHALL read slide content (track, title, bullets, reference links, lab steps) from a
structured, human-editable source file separate from the rendering code, so content can be
revised without changing the generator.

#### Scenario: Editing content without touching code

- **WHEN** a maintainer edits a bullet or reference URL in the content source
- **THEN** re-running the generator reflects the change with no code edits

### Requirement: Pipeline is tooling-only and documented

The generator SHALL depend on python-pptx as a build-time/tooling dependency only, MUST NOT be
imported by the `wxcc-mcp-server` runtime, and SHALL ship with a documented command to build the
deck.

#### Scenario: Runtime is unaffected

- **WHEN** the `wxcc-mcp-server` package and its tests are run
- **THEN** they neither import nor require python-pptx

#### Scenario: Documented build command

- **WHEN** a maintainer follows the lab-materials README
- **THEN** a single documented command regenerates the `.pptx` from the template and content source
