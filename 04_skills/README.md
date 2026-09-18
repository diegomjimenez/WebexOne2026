# Lab 4 — Agent Skills in VS Code

This folder contains the `meeting-review` skill for **Lab 4**. Attendees use it
directly inside VS Code Chat (Agent mode) — no code, no Python, no loader.

## What's here

```
04_skills/
  skills/
    meeting-review/SKILL.md    the skill file
  README.md                    this file
```

## How it works

VS Code Chat (Agent mode) supports [Agent Skills](https://agentskills.io/home) —
folders containing a `SKILL.md` file that the agent loads on demand.

The `.vscode/settings.json` in this repo already points the agent at this folder:

```json
{
  "chat.agentSkillsLocations": {
    "04_skills/skills": true
  }
}
```

When you open Chat and ask about meetings, the agent reads the `meeting-review`
skill's frontmatter (`name` + `description`), decides it's relevant, loads the
full body, and follows its instructions — checking participants, summaries,
recordings, and transcripts for every meeting.

## Prerequisites

| Requirement | How to set up |
|---|---|
| VS Code **>= 1.108** | `Help > About` |
| Agent Skills enabled | Settings → `chat.useAgentSkills` → enable |
| OpenAI model configured | Lab 1 Step 1.2 — `Chat: Manage Language Models` → OpenAI → enter API key |
| Webex Meeting MCP connected | Lab 1 — add the meeting server to `.vscode/mcp.json` |

## Try it

1. Open **Chat** (`Ctrl+Shift+P` → `Chat: Open Chat (Agent)`).
2. Make sure the **Webex Meeting MCP** is started.
3. Ask:

   > Review the meetings for user1@webexone-ai-assistant.wbx.ai. Check who
   > joined the past meetings, whether summaries and recordings exist, and
   > flag anything missing. For upcoming meetings, check if there's an agenda.

4. Watch the agent load `meeting-review` and investigate each meeting across
   multiple dimensions — not just a flat list.

You can also invoke it explicitly: type `/meeting-review` in the chat.

## What to observe (the skill's added value)

**Without the skill** (temporarily remove `chat.agentSkillsLocations` and reload):
the agent lists meetings and stops — one tool call, one scope.

**With the skill**: the agent calls multiple tools per meeting (participants,
summary, recording, transcript), flags missing artifacts, triages missed meetings,
and produces a prioritized action list.

Same tools, same data — the skill supplies the judgment.

## Next: Lab 7

In Lab 7 you build the Python **skill loader** that does what VS Code did here —
reading the *same* `meeting-review/SKILL.md`, unchanged — and wire it into a bot.
See `07_skills_bot/` and the lab guide at `LAB-31123/docs/lab7_skills.md`.
