"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Ask one question twice: once with meeting-review off, once with it on.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

LAB_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB_ROOT / "06_mcp_bot"))

from llm import as_openai_tools, run_turn
from mcp_client import McpClient
from skill_loader import SkillLoader

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

MEETING_MCP_URL = "https://mcp.webexapis.com/mcp/webex-meeting"
QUESTION = "Help me prepare for my upcoming Webex meetings."
SKILLS_DIR = Path(__file__).resolve().parent / "skills"

# Used only when WEBEX_MEETING_MCP_TOKEN is not set, so the comparison still runs.
CANNED_MEETINGS = {
    "items": [
        {
            "id": "sample-planning",
            "title": "Planning Session",
            "start": "2026-09-27T08:00:00Z",
            "end": "2026-09-27T09:00:00Z",
            "agenda": "",
            "invitees": [
                {"email": "admin@webexone-ai-assistant.wbx.ai", "displayName": "Admin"}
            ],
        },
        {
            "id": "sample-architecture",
            "title": "Architecture Review",
            "start": "2026-09-27T12:00:00Z",
            "end": "2026-09-27T13:00:00Z",
            "agenda": "Review the target architecture.",
            "invitees": [
                {"email": "admin@webexone-ai-assistant.wbx.ai", "displayName": "Admin"}
            ],
        },
    ]
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("skills-compare")

load_dotenv(LAB_ROOT / ".env")


class _Tool:
    def __init__(self, name, description, input_schema):
        self.name = name
        self.description = description
        self.input_schema = input_schema


class SampleMeetings:
    """Stand-in for the Meetings MCP server. One tool, fixed data."""

    async def list_tools(self):
        return [
            _Tool(
                "webex-list-meetings",
                "List Webex meetings for the authenticated user.",
                {
                    "type": "object",
                    "properties": {
                        "includeParticipants": {"type": "boolean"},
                    },
                },
            )
        ]

    async def call_tool(self, name, arguments=None):
        if name != "webex-list-meetings":
            return json.dumps({"error": f"Unknown tool: {name}"})
        return json.dumps(CANNED_MEETINGS)


async def ask(mcp, tools, system):
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": QUESTION},
    ]
    return await run_turn(mcp, messages, tools)


async def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Set OPENAI_API_KEY in your .env file")

    skill = SkillLoader(SKILLS_DIR).get_skill("meeting-review")
    if skill is None:
        raise SystemExit(f"Skill meeting-review was not found in {SKILLS_DIR}")

    token = os.getenv("WEBEX_MEETING_MCP_TOKEN")
    if token:
        mcp = McpClient(token, MEETING_MCP_URL)
        tools = as_openai_tools(await mcp.list_tools())
        log.info("Using the Webex Meetings MCP server.")
    else:
        tools = []
        log.info("WEBEX_MEETING_MCP_TOKEN is not set. Using the sample dataset.")

    if not tools:
        if token:
            log.info("The Meetings MCP server returned no tools. Using the sample dataset.")
        mcp = SampleMeetings()
        tools = as_openai_tools(await mcp.list_tools())

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    base = (
        f"You help a Webex user with their meetings. Today is {today} (UTC). "
        "Answer only from tool results, never from memory, and keep replies short."
    )
    with_skill = base + "\n\nFollow this runbook exactly:\n\n" + skill.instructions

    print("WITHOUT skill")
    print("-------------")
    print(await ask(mcp, tools, base))
    print()
    print("WITH skill")
    print("----------")
    print(await ask(mcp, tools, with_skill))


if __name__ == "__main__":
    asyncio.run(main())
