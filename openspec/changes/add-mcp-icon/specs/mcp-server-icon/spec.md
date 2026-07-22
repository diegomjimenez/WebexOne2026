## ADDED Requirements

### Requirement: Server exposes a branded icon via MCP protocol
The wxcc-mcp-server SHALL include an `icons` array in its `ServerInfo` during the MCP `initialize` handshake. The icon SHALL be a PNG image encoded as a base64 data URI.

#### Scenario: Client receives icon on initialize
- **WHEN** an MCP client connects and sends an `initialize` request
- **THEN** the server's response `serverInfo.icons` SHALL contain at least one entry with `src` set to a valid `data:image/png;base64,...` URI and `mimeType` set to `"image/png"`

### Requirement: Icon asset stored in repository
The original PNG asset SHALL be stored at `wxcc-mcp-server/assets/icon.png` so that it can be re-encoded or resized in the future without depending on external paths.

#### Scenario: Asset file exists in repo
- **WHEN** a developer clones the repository
- **THEN** the file `wxcc-mcp-server/assets/icon.png` SHALL exist and be a valid PNG image

### Requirement: Icon data isolated from main server module
The base64-encoded icon data SHALL be stored in a separate module (`wxcc_mcp/icon.py`) rather than inline in `server.py` to maintain code readability.

#### Scenario: Icon module provides data URI constant
- **WHEN** the server imports `wxcc_mcp.icon`
- **THEN** the module SHALL export an `ICON_DATA_URI` string constant containing the full data URI and a pre-constructed `Icon` object named `SERVER_ICON`
