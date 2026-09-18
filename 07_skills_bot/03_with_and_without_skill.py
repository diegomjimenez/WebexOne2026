"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Why do skills matter? Same agent, same question — with and without a skill.
This example reuses the 04_mcp Webex Meetings MCP agent (llm.py + mcp_client.py)
and runs the same question twice, printing both answers side by side.

The skill tells the agent to INVESTIGATE every meeting across multiple Webex
Meeting MCP scopes (participants, summaries, recordings, transcripts) — not
just list the schedule. Without the skill, the model uses 1 scope. With it,
the model uses 5. That's the added value.

When WEBEX_MEETING_MCP_TOKEN is not set, a canned meeting dataset is used so the
demo still works without a Meetings tenant.

Reference: https://agentskills.io/home  (Why Agent Skills?)
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- Reuse the 04_mcp agent by import (design decision: import, not copy) ---
_MCP_DIR = str(Path(__file__).resolve().parent.parent / "06_mcp_bot")
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from dotenv import load_dotenv

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

from llm import as_openai_tools, run_turn  # noqa: E402
from mcp_client import McpClient  # noqa: E402

# ---------------------------------------------------------------------------

SKILLS_DIR = Path(__file__).parent / "skills"
SKILL_NAME = "meeting-review"
MEETING_MCP_URL = "https://mcp.webexapis.com/mcp/webex-meeting"
QUESTION = "Review the meetings for user1@webexone-ai-assistant.wbx.ai — check participants, summaries, recordings, and flag anything missing."

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("skills-value")

load_dotenv()

MEETING_TOKEN = os.getenv("WEBEX_MEETING_MCP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")

if not OPENAI_API_KEY:
    raise SystemExit("Set OPENAI_API_KEY in your .env file")

# ---------------------------------------------------------------------------
# Skill loader — uses the shared SkillLoader class
# ---------------------------------------------------------------------------

from skill_loader import SkillLoader


# ---------------------------------------------------------------------------
# Canned meeting data — exercises multiple scopes so the A/B contrast works
# without live MCP. Includes participants, summary, recording, transcript.
# ---------------------------------------------------------------------------

SAMPLE_MEETINGS = json.dumps({
    "meetings": [
        {
            "title": "Meeting with user1@webexone-ai-assistant.wbx.ai",
            "meetingNumber": "26601464108",
            "start": "2026-09-18T16:00:00Z",
            "end": "2026-09-18T17:00:00Z",
            "state": "ready",
            "host": "admin@webexone-ai-assistant.wbx.ai",
            "invitees": ["user1@webexone-ai-assistant.wbx.ai"],
            "agenda": None,
            "participants_who_joined": None,
            "summary": None,
            "recording": None,
            "transcript": None,
        },
        {
            "title": "Meeting with user1@webexone-ai-assistant.wbx.ai",
            "meetingNumber": "26604791633",
            "start": "2026-09-15T16:00:00Z",
            "end": "2026-09-15T17:00:00Z",
            "state": "missed",
            "host": "admin@webexone-ai-assistant.wbx.ai",
            "invitees": ["user1@webexone-ai-assistant.wbx.ai"],
            "agenda": None,
            "participants_who_joined": [],
            "summary": None,
            "recording": None,
            "transcript": None,
        },
    ],
    "note": "Data from Webex Meeting MCP scopes: schedules_read, participants_read, summaries_read, recordings_read, transcripts_read",
}, indent=2)


# ---------------------------------------------------------------------------
# Run a single query
# ---------------------------------------------------------------------------


async def run_query(system_content, use_mcp):
    """Run the LLM with the given system prompt; return the answer text."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if use_mcp:
        client = McpClient(MEETING_TOKEN, MEETING_MCP_URL)
        tools = as_openai_tools(await client.list_tools())
    else:
        client = None
        tools = []

    base_system = (
        f"You help a Webex user review their meetings. Today is {today} (UTC). "
        "Answer only from tool results or the data provided, never from memory."
    )
    full_system = base_system + "\n\n" + system_content if system_content else base_system

    messages = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": QUESTION},
    ]

    if not use_mcp:
        messages.append({
            "role": "user",
            "content": (
                "Here is the meeting data (includes schedule, participants, "
                "summary, recording, and transcript status for each meeting):\n"
                f"```json\n{SAMPLE_MEETINGS}\n```"
            ),
        })

    if client and tools:
        return await run_turn(client, messages, tools)
    else:
        import requests as _req

        def _ask_no_tools(msgs):
            r = _req.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                    "Content-Type": "application/json",
                },
                json={"model": OPENAI_MODEL, "messages": msgs},
                timeout=60,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]

        reply = await asyncio.to_thread(_ask_no_tools, messages)
        return reply.get("content") or "(no answer)"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    use_mcp = bool(MEETING_TOKEN)
    if not use_mcp:
        log.info("WEBEX_MEETING_MCP_TOKEN not set — using sample meeting data.")

    loader = SkillLoader(str(SKILLS_DIR))
    skill = loader.get_skill(SKILL_NAME)
    if not skill:
        raise SystemExit(f"Skill '{SKILL_NAME}' not found in {SKILLS_DIR}")
    skill_body = skill.instructions

    # --- Run 1: WITHOUT skill ---
    log.info("Run 1: WITHOUT skill (plain 04_mcp agent)")
    answer_without = await run_query(system_content="", use_mcp=use_mcp)

    # --- Run 2: WITH skill (same tools, skill body in system prompt) ---
    log.info("Run 2: WITH skill (skill body injected into system prompt)")
    answer_with = await run_query(system_content=skill_body, use_mcp=use_mcp)

    # --- Side-by-side output ---
    sep = "=" * 60
    print(f"\n{sep}")
    print("RESULTS — same agent, same question, same data")
    if not use_mcp:
        print("(using sample data — set WEBEX_MEETING_MCP_TOKEN for live meetings)")
    print(sep)

    print(f"\n{'─' * 60}")
    print("WITHOUT skill")
    print(f"{'─' * 60}")
    print(answer_without)

    print(f"\n{'─' * 60}")
    print("WITH skill (meeting-review)")
    print(f"{'─' * 60}")
    print(answer_with)

    print(f"\n{sep}")
    print(
        "The skill told the agent to INVESTIGATE, not just LIST.\n"
        "Without skill: 1 scope (schedule). With skill: 5 scopes\n"
        "(schedule + participants + summary + recording + transcript).\n"
        "Same tools, same data — the skill adds multi-scope judgment.\n"
        "\nThis is the added value of an Agent Skill."
    )
    print(sep)


if __name__ == "__main__":
    asyncio.run(main())
