## Context

The wxcc-mcp-server uses FastMCP (`mcp>=1.2.0`) which supports the MCP specification's `icons` field on `ServerInfo`. When a server provides icons during the `initialize` handshake, Cursor renders the icon in its MCP panel. Currently, the server is instantiated with `FastMCP("wxcc-mcp-server")` and no icon metadata.

The source image is a PNG screenshot at `C:\Users\mohamusa\OneDrive - Cisco\Pictures\Screenshots\webexone.png`.

## Goals / Non-Goals

**Goals:**
- Serve a branded WebexOne icon via the MCP protocol so Cursor displays it in the MCP server list
- Keep the icon self-contained (no external URL dependency) by using a data URI
- Store the original asset in the repository for future reference

**Non-Goals:**
- Hosting the icon on an external server
- Supporting multiple icon sizes or themes (single icon is sufficient for Cursor's current UI)
- Changing the server name or other metadata

## Decisions

### Decision 1: Use a base64 data URI for the icon source

**Choice:** Encode the PNG as a `data:image/png;base64,...` URI and pass it as the `src` field in the MCP `Icon` object.

**Rationale:** The server runs locally over stdio. There is no HTTP endpoint to serve static files from, so a data URI is the only reliable option that doesn't require hosting infrastructure. The MCP spec explicitly supports data URIs.

**Alternative considered:** Hosting the image at an HTTPS URL. Rejected because it introduces an external dependency, requires infrastructure, and would fail offline.

### Decision 2: Store the encoded constant in a dedicated module

**Choice:** Create `wxcc-mcp-server/src/wxcc_mcp/icon.py` containing a single constant `ICON_DATA_URI` and an `ICON` object.

**Rationale:** Keeps the large base64 string out of `server.py`, improving readability. The module is imported only at startup.

**Alternative considered:** Inline the data URI in `server.py`. Rejected because a base64-encoded PNG is typically 10-50KB of text which would clutter the main server module.

### Decision 3: Store the original PNG in an assets directory

**Choice:** Copy the original image to `wxcc-mcp-server/assets/icon.png` and commit it to the repository.

**Rationale:** Preserves the source asset for future edits (resizing, re-encoding) without depending on the user's OneDrive path.

## Risks / Trade-offs

- **Large encoded string in source** → Mitigated by isolating in `icon.py`; module is loaded once at import time and has negligible runtime cost.
- **Image too large for data URI** → If the PNG exceeds ~100KB, we should resize it to 128x128 or 64x64 before encoding. Most MCP icon UIs render at small sizes anyway.
- **Cursor client icon support bugs** → There was a known bug with `sizes` array validation (fixed in SDK 1.19.0+). We'll omit `sizes` to avoid any residual client issues.
