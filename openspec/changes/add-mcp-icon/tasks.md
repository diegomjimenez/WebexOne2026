## 1. Asset Preparation
`
- [x] 1.1 Resize the image to 128x128 if it exceeds 100KB (to keep the data URI reasonable)

## 2. Icon Module

- [x] 2.1 Create `wxcc-mcp-server/src/wxcc_mcp/icon.py` with base64-encoded data URI constant (`ICON_DATA_URI`) and a pre-built `SERVER_ICON` object using `mcp.types.Icon`

## 3. Server Integration

- [x] 3.1 Update `FastMCP("wxcc-mcp-server")` call in `server.py` to pass `icons=[SERVER_ICON]`
- [x] 3.2 Add the import of `SERVER_ICON` from `wxcc_mcp.icon` in `server.py`

## 4. Verification

- [ ] 4.1 Restart the MCP server and confirm Cursor shows the icon in the MCP panel
