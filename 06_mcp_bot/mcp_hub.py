"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Several MCP servers, one list of tools. The LLM picks a tool name; we route the call.
"""

from mcp_client import McpClient


class McpHub:
    def __init__(self, servers):
        self.clients = []
        for item in servers:
            if isinstance(item, McpClient):
                self.clients.append(item)
            else:
                url, token = item
                if token:
                    self.clients.append(McpClient(token, url))
        self._by_name = {}

    async def list_tools(self):
        tools = []
        self._by_name = {}
        for client in self.clients:
            for tool in await client.list_tools():
                self._by_name[tool.name] = client
                tools.append(tool)
        return tools

    async def call_tool(self, name, arguments=None):
        if name not in self._by_name:
            await self.list_tools()
        client = self._by_name.get(name)
        if client is None:
            raise KeyError(f"Unknown MCP tool: {name}")
        return await client.call_tool(name, arguments)
