# Lab 7 — Python Skill Loader + Bot Integration

This folder contains the **advanced** skills material for Lab 7. In Lab 4 you
used the `meeting-review` skill inside VS Code Chat (Agent mode) with zero code.
Here you build and own the Python mechanism that does the same thing, then
onboard a second skill.

## What's here

```
07_skills_bot/
    skills/
        meeting-review/SKILL.md              primary (same file as Lab 4)
        troubleshoot-address-books/SKILL.md  second skill (onboarded here)
    01_what_is_a_skill.py        discover skills, parse frontmatter
    02_progressive_disclosure.py summary vs body (3 stages)
    03_with_and_without_skill.py value A/B: same agent, skill off vs on
    README.md                    this file
    requirements.txt
    .env.example
```

## Setup

```bash
cd 07_skills_bot
pip install -r requirements.txt
cp .env.example .env    # then edit .env
```

- `01` and `02` need NO credentials.
- `03` needs `OPENAI_API_KEY`. The Meetings MCP token is optional (canned data
  fallback).

## The arc (continuity from Lab 4)

```
Lab 4 (VS Code Chat)           Lab 7 (this folder + capstone bot)
-----------------               ----------------------------------
meeting-review              ->  1. recap: same file from Lab 4
used with zero code             2. build the loader (see webex-mcp-lab/agent_bot/utils/skills.py)
                                3. put meeting-review in action via the bot
                                4. onboard troubleshoot-address-books (second skill)
```

## Onboarding a second skill (no code change)

The loader scans a directory. `skills/` already has both skills — run
`python 01_what_is_a_skill.py` and both appear.

## Integrated bot

The capstone bot at `webex-mcp-lab/agent_bot` ships a production loader
(`utils/skills.py`). Point its `SKILLS_DIR` at `../07_skills_bot/skills` so it
discovers both skills. Note: `troubleshoot-address-books` needs the capstone
address-book and desktop-profile MCP servers connected.
