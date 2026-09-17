"""MCP client: one session per server URL, list tools, and call them."""

import logging
import traceback
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client

logging.getLogger("mcp.client.streamable_http").addFilter(
    lambda record: "Error parsing SSE message" not in record.getMessage()
)


class McpClient:
    """One MCP session = one server URL + that server's token."""

    def __init__(self, access_token, url):
        self.access_token = access_token
        self.url = url

    @asynccontextmanager
    async def session(self):
        http = create_mcp_http_client(headers={"Authorization": f"Bearer {self.access_token}"})
        async with http:
            async with streamable_http_client(self.url, http_client=http) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

    async def list_tools(self):
        try:
            async with self.session() as session:
                return (await session.list_tools()).tools
        except Exception as e:
            # The SDK runs the transport in a task group, so the real error is nested.
            traceback.print_exception(e, limit=0)
            return []

    async def call_tool(self, name, arguments=None):
        try:
            async with self.session() as session:
                result = await session.call_tool(name, arguments or {})
                texts = [c.text for c in result.content if getattr(c, "type", None) == "text"]
                return "\n".join(texts) if texts else str(result.content)
        except Exception as e:
            traceback.print_exception(e, limit=0)
            return None
