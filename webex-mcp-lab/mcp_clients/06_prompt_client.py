"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Test client for 06_prompt.py - exercises prompts, resources, AND tools.
# Lists prompts and gets one with sample arguments, then lists resources/tools.
#
#     python mcp_clients/06_prompt_client.py            # high-level output
#     python mcp_clients/06_prompt_client.py --verbose  # + raw JSON-RPC frames

from __future__ import annotations

from mcp import Client

from run_client import banner, run_client


async def exercise(client: Client) -> None:
    banner("Prompts")
    prompts = await client.list_prompts()
    for p in prompts.prompts:
        print(f"  {p.name}: {p.description[:80] if p.description else ''}")

    if prompts.prompts:
        prompt = prompts.prompts[0]
        banner(f"Get prompt: {prompt.name}")
        result = await client.get_prompt(
            prompt.name,
            arguments={"book_name": "Sales - EMEA", "team": "EMEA"},
        )
        for msg in result.messages:
            role = msg.role
            text = msg.content.text if hasattr(msg.content, "text") else str(msg.content)
            print(f"  [{role}] {text}")

    banner("Resources")
    resources = await client.list_resources()
    for r in resources.resources:
        print(f"  {r.uri}: {r.description[:60] if r.description else ''}")

    banner("Tools")
    tools = await client.list_tools()
    for t in tools.tools:
        print(f"  {t.name}: {t.description[:80] if t.description else ''}")


if __name__ == "__main__":
    run_client("06_prompt.py", exercise, description="Test client for 06_prompt.py")
