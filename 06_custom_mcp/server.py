"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Custom MCP Server for Webex Organizational Troubleshooting.
"""

import asyncio
import os
import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("webex-custom-lab")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="webex_status_unresolved",
            description="List unresolved Webex platform incidents.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        Tool(
            name="list_admin_audit_events",
            description="List recent admin audit events for troubleshooting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "max": {
                        "type": "integer", 
                        "description": "Maximum number of events to return",
                        "default": 10
                    }
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "webex_status_unresolved":
        response = requests.get("https://status.webex.com/api/v2/incidents/unresolved.json", timeout=30)
        response.raise_for_status()
        return [TextContent(type="text", text=response.text)]
        
    elif name == "list_admin_audit_events":
        max_results = arguments.get("max", 10)
        token = os.getenv("ACCESS_TOKEN")
        if not token:
            return [TextContent(type="text", text="Error: ACCESS_TOKEN environment variable not set.")]
        
        response = requests.get(
            "https://webexapis.com/v1/adminAudit/events",
            headers={"Authorization": f"Bearer {token}"},
            params={"max": max_results},
            timeout=30,
        )
        response.raise_for_status()
        return [TextContent(type="text", text=response.text)]
        
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
