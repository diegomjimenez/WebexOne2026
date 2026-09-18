"""OpenAI Chat Completions + MCP tool loop. The host (script or bot) supplies the tools."""

import asyncio
import json
import logging
import os

import requests

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MAX_STEPS = 5

log = logging.getLogger("mcp-llm")


def ask_llm(messages, tools):
    """One Chat Completions round. Returns the assistant message (text or tool calls)."""
    response = requests.post(
        OPENAI_URL,
        headers={
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.getenv("OPENAI_MODEL", "gpt-5-nano"),
            "messages": messages,
            "tools": tools,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]


def as_openai_tools(mcp_tools):
    # An MCP tool already describes itself with a JSON schema, which is what OpenAI wants.
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }
        for tool in mcp_tools
    ]


async def run_turn(mcp, messages, tools, max_steps=MAX_STEPS, extra=None):
    extra = extra or {}
    for _ in range(max_steps):
        message = await asyncio.to_thread(ask_llm, messages, tools)
        messages.append(message)

        tool_calls = message.get("tool_calls")
        if not tool_calls:
            return message.get("content") or "(no answer)"

        for call in tool_calls:
            name = call["function"]["name"]
            arguments = json.loads(call["function"]["arguments"] or "{}")
            log.info(f"LLM asked for {name} {arguments}")
            if name in extra:
                result = extra[name](arguments)
            else:
                result = await mcp.call_tool(name, arguments)
            messages.append(
                {"role": "tool", "tool_call_id": call["id"], "content": result or "Tool error"}
            )

    return f"Stopped after {max_steps} tool steps without a final answer."
