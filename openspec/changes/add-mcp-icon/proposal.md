## Why

The wxcc-mcp-server currently has no visual icon in Cursor's MCP panel, making it harder to identify among other configured MCP servers. Adding a branded WebexOne icon improves discoverability and provides visual consistency with the Cisco/Webex product family.

## What Changes

- Copy the WebexOne PNG image into the server's assets directory
- Encode the image as a base64 data URI and register it via FastMCP's `icons` parameter
- The server will expose the icon through the MCP protocol's `ServerInfo` during initialization, which Cursor renders in its MCP panel

## Capabilities

### New Capabilities
- `mcp-server-icon`: Add a branded icon to the wxcc-mcp-server that is exposed via the MCP protocol's ServerInfo icons field

### Modified Capabilities

## Impact

- `wxcc-mcp-server/src/wxcc_mcp/server.py` — updated to pass `icons` list to `FastMCP()` constructor
- New asset file at `wxcc-mcp-server/assets/icon.png`
- New module `wxcc-mcp-server/src/wxcc_mcp/icon.py` to hold the base64-encoded data URI constant
