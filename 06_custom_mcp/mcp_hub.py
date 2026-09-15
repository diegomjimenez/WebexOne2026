"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Combines multiple McpClients into a single toolset for the LLM.
"""

from mcp_client import McpClient

class McpHub:
    def __init__(self, servers):
        self.clients = []
        for s in servers:
            if isinstance(s, McpClient):
                self.clients.append(s)
            else:
                url, token = s
                if token:
                    self.clients.append(McpClient(access_token=token, url=url))
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
            return f"Error: Tool {name} not found in any MCP server."
        return await self._by_name[name].call_tool(name, arguments)
