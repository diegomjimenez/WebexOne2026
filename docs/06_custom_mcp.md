# Lab 6 - Build a Custom MCP Server

In this section, you will build a custom MCP server that exposes Webex API operations your organization needs — beyond what the official Webex MCP servers provide out of the box.

In this case, we will build an MCP Server that will help us to do **organizational troubleshooting** actions in our organization, specifically checking the Webex platform status and retrieving admin audit logs.

## Step 6.1: Defining and Implementing Tools

We will use the official `mcp` Python SDK to create our server. The SDK makes it incredibly easy to define tools and their execution logic using decorators.

1. Navigate to `06_custom_mcp/server.py` and review the code.

    This script defines two tools:
    - `webex_status_unresolved`: Lists unresolved Webex platform incidents.
    - `list_admin_audit_events`: Lists recent admin audit events for troubleshooting.

    ??? Tip "Python Code"
        ```python
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
            # Run the server using standard input/output streams
            async with stdio_server() as (read_stream, write_stream):
                await app.run(read_stream, write_stream, app.create_initialization_options())

        if __name__ == "__main__":
            asyncio.run(main())
        ```

!!! Note
    Production MCP servers should validate arguments against JSON Schema, apply rate limits, redact sensitive fields, and use elicitation for destructive operations.

## Step 6.2: Register in your IDE

In this section, you will add and test your custom MCP server directly in VS Code.

1. Open the `.vscode/mcp.json` file.
2. Add the `webex-custom-lab` server configuration to the `servers` object. Make sure to replace `YOUR_SERVICE_APP_TOKEN` with the `ACCESS_TOKEN` from your `.env` file, and update the absolute path to your `server.py` file.

    ```json
    {
      "servers": {
        "webex-messaging": {
          "type": "stdio",
          "command": "npx",
          "args": [
            "-y",
            "mcp-remote",
            "https://mcp.webexapis.com/mcp/webex-messaging",
            "--header",
            "Authorization: Bearer WEBEX_MCP_TOKEN"
          ]
        },
        "webex-custom-lab": {
          "command": "python",
          "args": ["/ABSOLUTE/PATH/TO/05-bots/06_custom_mcp/server.py"],
          "env": {
            "ACCESS_TOKEN": "YOUR_SERVICE_APP_TOKEN"
          }
        }
      }
    }
    ```

3. Reload the VS Code window for the changes to take effect (`Ctrl+Shift+P` -> "Developer: Reload Window").
4. Open the Agent Chat and test your new tools:

    ```text
    Use the webex-custom-lab server to list unresolved platform incidents.
    ```

    ```text
    Use list_admin_audit_events to show the last 5 admin changes in our org.
    ```

## Step 6.3: Integrate with your AI Assistant

Now, you will add your custom MCP server to your AI assistant. 

Unlike the official Webex MCP servers which run remotely and connect via HTTP (Server-Sent Events), our custom server runs locally over standard input/output (`stdio`). We have updated the `McpClient` class to seamlessly support both connection types!

1. Navigate to `06_custom_mcp/01_custom_bot.py` and review the code.

    Notice how we initialize two different `McpClient` instances and combine them in the `McpHub`:

    ??? Tip "Python Code"
        ```python
        # 1. Create the remote client (Messaging MCP)
        messaging_client = McpClient(access_token=service_app_token, url=MESSAGING_MCP_URL)

        # 2. Create the local custom client (stdio)
        server_script = str(Path(__file__).resolve().parent / "server.py")
        custom_client = McpClient(
            command="python", 
            args=[server_script], 
            env={"ACCESS_TOKEN": service_app_token}
        )

        # 3. Combine them in the Hub
        hub = McpHub([messaging_client, custom_client])
        ```

2. Run your bot:

    ```bash
    cd ../06_custom_mcp
    python 01_custom_bot.py
    ```

3. Go to your Webex Client and ask your bot:

    > Are there any unresolved Webex incidents?

    > What were the last 3 admin audit events in our organization?

Congratulations! You have successfully built a custom MCP server, tested it in your IDE, and integrated it into a production-ready AI Assistant.
