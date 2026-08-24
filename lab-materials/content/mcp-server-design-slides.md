# MCP Server Design — Presentation Slides

Reference document combining the [official MCP Architecture spec (2026-07-28)](https://modelcontextprotocol.io/specification/2026-07-28/architecture) with the wxcc-mcp-server implementation for WebexOne presentation.

---

## Slide 1 — MCP Architecture: Spec Diagram → Your Reality

### Left side: The spec's architecture

```
┌─────── Application Host (Claude Desktop) ──────┐
│                                                 │
│   Host                                          │
│    ├── Client 1 ──── Server 1 (Files & Git)     │
│    ├── Client 2 ──── Server 2 (Database)        │
│    └── Client 3 ──── Server 3 (External APIs)   │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Right side: Your WebexOne reality

```
┌─────── Cursor IDE (Host) ──────────────────────┐
│                                                 │
│   Cursor                                        │
│    ├── Client ──── wxcc-mcp-server (your lab)   │
│    │                 • 18 tools                  │
│    │                 • 3 resources               │
│    │                 • 3 prompts                 │
│    │                 • elicitation-gated writes  │
│    │                                            │
│    ├── Client ──── GitHub MCP server            │
│    └── Client ──── Filesystem server            │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Key bridge sentence:**
> The spec defines the shape. Your server fills one of those boxes with real Webex Contact Center capabilities.

---

## Slide 2 — Four Design Principles (Spec → Implementation)

From the [official spec](https://modelcontextprotocol.io/specification/2026-07-28/architecture):

| Spec Principle | What It Says | How Your Server Does It |
|---|---|---|
| **Easy to build** | Host handles orchestration; servers focus on capabilities | `server.py` is thin wrappers; FastMCP handles the protocol; you just write tool functions |
| **Highly composable** | Each server provides focused functionality in isolation | Your server does WxCC only — address books, entries, profiles. Nothing else. |
| **Cannot see the conversation or other servers** | Servers receive only necessary contextual information | Your tools get `org_id` and IDs — never the chat history, never another server's data |
| **Progressive features** | Core protocol is minimal; capabilities added incrementally | You started with tools, then added resources, then prompts, then elicitation — each opt-in |

### Speaker notes

> These aren't abstract rules. Look at principle 3 — "servers cannot see the conversation." In our server, a tool receives `org_id` and `address_book_id`. That's it. It has no idea what the user said, what other tools were called before it, or what the GitHub server is doing in another client session. The host decides what context to share. The server just does its job with the parameters it gets.
>
> Principle 1 is the reason we use FastMCP. The host — Cursor, Claude Desktop — handles all the JSON-RPC negotiation, capability advertisement, and transport management. Our server just decorates functions with `@mcp.tool()` and returns dictionaries. The framework does the rest.

---

## Slide 3 — Capability Negotiation (Spec Lifecycle → Your Server)

**The spec says:**
> "Clients include their capabilities in `_meta.io.modelcontextprotocol/clientCapabilities` on every request. Servers advertise capabilities in response to `server/discover`."

### What this looks like with your server

```
    CLIENT (Cursor)                     YOUR SERVER
        │                                   │
        │   server/discover                 │
        │ ──────────────────────────────▶   │
        │                                   │
        │   ◀────── capabilities: ────────  │
        │     tools:     { listChanged: true }
        │     resources: { subscribe: true, listChanged: true }
        │     prompts:   { listChanged: true }
        │                                   │
        │                                   │
        │   tools/list                      │
        │ ──────────────────────────────▶   │
        │                                   │
        │   ◀────── 18 tools ─────────────  │
        │     tool_list_address_books       │
        │     tool_create_address_book      │
        │     tool_delete_address_book      │
        │     ...                           │
        │                                   │
        │   resources/list                  │
        │ ──────────────────────────────▶   │
        │                                   │
        │   ◀────── 3 resources ──────────  │
        │     wxcc://reference/address-book-schema
        │     wxcc://reference/write-safety-guide
        │     wxcc://crm/contacts           │
        │                                   │

   If the server didn't declare "tools" in capabilities,
   the client would NEVER call tools/list.
```

### Speaker notes

> Capabilities are the contract. The server declares what it can do. The client respects those boundaries. If you add prompts but forget to declare the prompts capability, no client will ever ask for them. This is exactly what happened when we first tested — prompts weren't appearing because the capability wasn't advertised.

---

## Slide 4 — Server Isolation in Practice

**The spec says:**
> "Servers receive only necessary contextual information. Full conversation history stays with the host. Each server maintains isolation."

```
┌─── HOST (Cursor) ─────────────────────────────────────────┐
│                                                            │
│  Chat history: "Hey, can you sync my CRM contacts         │
│  into the Sales address book and assign it to the          │
│  support team profile?"                                    │
│                                                            │
│  The model decomposes this into tool calls:                │
│                                                            │
│  ┌──────────────────────────────────────────────────┐      │
│  │  What the MODEL sees:                            │      │
│  │  Full conversation + all server catalogs         │      │
│  └──────────────────────────────────────────────────┘      │
│                                                            │
│  ┌──────────────────────────────────────────────────┐      │
│  │  What the SERVER receives:                       │      │
│  │                                                  │      │
│  │  tools/call: tool_sync_crm_to_address_book       │      │
│  │  arguments: {                                    │      │
│  │    org_id: "12345",                              │      │
│  │    address_book_id: "ab-001",                    │      │
│  │    confirm: false                                │      │
│  │  }                                               │      │
│  │                                                  │      │
│  │  That's ALL. No chat. No user name. No other     │      │
│  │  server's responses. Just the typed parameters.  │      │
│  └──────────────────────────────────────────────────┘      │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Speaker notes

> This is the security payoff. The server has no access to the conversation. It doesn't know what the user asked. It doesn't know what other servers returned. It receives typed parameters and executes. The host is the only entity that sees everything — and it decides what to share and what to withhold.

---

## Slide 5 — Server Anatomy: The Layered Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        server.py                               │
│              (registration + wiring — thin layer)              │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌────────────┐   ┌────────────┐   ┌────────────────────────┐ │
│  │  TOOLS     │   │ RESOURCES  │   │       PROMPTS          │ │
│  │            │   │            │   │                        │ │
│  │ 18 funcs   │   │ 3 static   │   │ 3 template builders   │ │
│  │ read/write │   │ reference  │   │ workflow guidance      │ │
│  └─────┬──────┘   └────────────┘   └────────────────────────┘ │
│        │                                                       │
├────────┼───────────────────────────────────────────────────────┤
│        │          _runtime.py                                  │
│        │   (cross-cutting: logging, timing, elicitation,       │
│        │    progress, error translation, sampling)             │
├────────┼───────────────────────────────────────────────────────┤
│        ▼                                                       │
│  ┌────────────┐   ┌────────────┐   ┌────────────────────────┐ │
│  │  tools/    │   │  models/   │   │      api/              │ │
│  │            │   │            │   │                        │ │
│  │ business   │   │ Pydantic   │   │ HTTP client, retries,  │ │
│  │ logic      │   │ schemas    │   │ auth injection         │ │
│  └────────────┘   └────────────┘   └────────────────────────┘ │
│                                                                │
│  ┌────────────┐   ┌─────────────────────────────────────────┐ │
│  │  auth/     │   │           config.py                     │ │
│  │  OAuth     │   │   endpoints, settings, env vars         │ │
│  └────────────┘   └─────────────────────────────────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Key point:** The server.py file is thin — it only registers and wires. Business logic lives in `tools/`, protocol machinery in `_runtime.py`, and HTTP concerns in `api/`.

### Speaker notes

> This is what "easy to build" looks like in practice. The top layer — server.py — is nothing but `@mcp.tool()` decorators calling into the layers below. You could read the entire file in five minutes and understand every tool. The complexity lives in `_runtime.py` (protocol helpers) and `api/` (HTTP client), but you never need to touch those to add a new tool. You just write a function and decorate it.

---

## Slide 6 — The Tool Pattern: Every Tool Has the Same Shape

```
Every tool in this server makes three moves:

  ┌─────────────────────────────────────────────────────┐
  │                                                     │
  │  ① RESOLVE the per-session API client               │
  │     → get_client()                                  │
  │                                                     │
  │  ② MAP arguments to a typed schema and call logic   │
  │     → address_books.run_create(client, sid, Input)  │
  │                                                     │
  │  ③ WRAP in run_tool() for observability             │
  │     → timing, correlation ID, structured logging,   │
  │       error translation to plain text               │
  │                                                     │
  └─────────────────────────────────────────────────────┘

  For WRITE tools, add one step before ②:

  ┌─────────────────────────────────────────────────────┐
  │                                                     │
  │  ①½ GATE via should_commit()                        │
  │      → elicitation form or dry-run/confirm fallback │
  │      → no approval = no commit, ever                │
  │                                                     │
  └─────────────────────────────────────────────────────┘
```

**Key point:** Read one tool, you've read them all. Consistency is the design goal.

### Speaker notes

> This is deliberate. When someone joins the team — or when attendees build their own server in this lab — they don't need to understand the entire codebase. They read one tool function, see the three moves, and can write the next one in two minutes. The pattern is the documentation.

---

## Slide 7 — The Safety Layer: Defense-in-Depth for Writes

```
       User says: "Delete address book Sales Team"
                          │
                          ▼
  ┌──── LAYER 1: Schema Validation ────────────────────┐
  │  Pydantic rejects malformed inputs immediately     │
  └─────────────────────┬─────────────────────────────┘
                        │
                        ▼
  ┌──── LAYER 2: Elicitation Gate ─────────────────────┐
  │  "Confirm: delete address book Sales Team?"        │
  │  Human must approve. LLM cannot bypass.            │
  └─────────────────────┬─────────────────────────────┘
                        │
                        ▼
  ┌──── LAYER 3: Risk Classification ──────────────────┐
  │  HIGH risk = read first + one-at-a-time + verify   │
  │  MEDIUM risk = preview + approve + verify          │
  └─────────────────────┬─────────────────────────────┘
                        │
                        ▼
  ┌──── LAYER 4: API Error Translation ────────────────┐
  │  HTTP errors become plain-text explanations        │
  │  No raw stack traces reach the model               │
  └────────────────────────────────────────────────────┘
```

### Speaker notes

> Four layers, and the LLM can't skip any of them. Layer 1 is automatic — Pydantic rejects bad types before your code even runs. Layer 2 is the human gate — the server pauses and asks. Layer 3 determines how much ceremony surrounds the write. Layer 4 ensures that even if something goes wrong at the API level, the model gets useful feedback instead of a 500 stack trace.

---

## Slide 8 — Observability: What You Log and Where

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  stdout  ──▶  JSON-RPC ONLY (protocol messages)             │
│               Never touch this. One stray print = broken.    │
│                                                              │
│  stderr  ──▶  Structured logs (JSON)                        │
│               Every tool call emits:                         │
│                                                              │
│               { "event": "tool.received",                    │
│                 "tool": "create_address_book",               │
│                 "request_id": "abc123",                      │
│                 "intent": "create book CRM Contacts" }       │
│                                                              │
│               { "event": "tool.result",                      │
│                 "tool": "create_address_book",               │
│                 "request_id": "abc123",                      │
│                 "elapsed_ms": 342 }                          │
│                                                              │
│  file    ──▶  Optional debug log (wxcc_debug.log)           │
│               Same events, persistent for post-mortem        │
│                                                              │
│  NEVER:  Secrets, tokens, raw API responses in any log      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Speaker notes

> The critical rule: stdout is sacred. It carries only JSON-RPC messages between client and server. One `print("debug")` on stdout breaks the entire protocol stream. All your logging goes to stderr, which the host captures separately. We use structlog to emit JSON events with correlation IDs so you can trace a tool call from receipt to result.

---

## Slide 9 — Design Decisions Table

| Decision | Choice | Why |
|---|---|---|
| Server framework | FastMCP (Python) | Decorator-based, minimal boilerplate, teaches clearly |
| Tool shape | Thin wrappers in server.py | Keeps registration separate from logic |
| Validation | Pydantic schemas for every input | Type safety + auto-generated JSON schema for the catalog |
| Auth | OAuth broker, per-session, never exposed to model | Token never in tool args or responses |
| Writes | Always gated (elicitation or confirm flag) | No accidental mutations |
| Errors | Translated to plain text for the LLM | Models don't parse HTTP 403s well |
| Logging | stderr only, structured JSON, correlation IDs | Debuggable without polluting stdio |
| Resources | Static reference data, not live queries | Model reads rules once, applies them repeatedly |

---

## Slide 10 — Anti-Patterns: What NOT to Do

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  ✗  One giant "do_anything" tool                         │
│     → Build single-purpose tools with clear boundaries   │
│                                                          │
│  ✗  Trusting the LLM to validate inputs                 │
│     → Validate in server code, not in prompts            │
│                                                          │
│  ✗  Logging to stdout                                    │
│     → Breaks the JSON-RPC stream immediately             │
│                                                          │
│  ✗  Returning raw API responses to the model             │
│     → Filter, summarize, translate to useful context     │
│                                                          │
│  ✗  Hardcoding credentials in tool arguments             │
│     → Broker tokens per-session; never expose to model   │
│                                                          │
│  ✗  Auto-committing writes without human approval        │
│     → Gate every mutation with elicitation or confirm    │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Slide 11 — Summary: Spec Principles as Your Server's DNA

| Spec Says | Your Server Proves It |
|---|---|
| Stateless: every request is self-contained | Each tool call carries `org_id` + IDs — no session memory needed |
| Servers are easy to build | 33 Python files. `@mcp.tool()` decorator. That's the registration. |
| Servers are composable | WxCC server + GitHub server + filesystem server coexist in Cursor |
| Servers can't see the conversation | Tools receive only their declared parameters, nothing else |
| Features added progressively | Tools first, then resources, then prompts, then elicitation — all opt-in |
| Capability negotiation governs everything | No `prompts` declaration = no prompts visible to any client |

**Footer:**
> The spec is the rulebook. Your server is the game. Every design decision traces back to a principle.

---

## Recommended Slide Sequence

| # | Slide | One-line purpose |
|---|---|---|
| 1 | Architecture: Spec → Reality | Show where your server sits in the MCP picture |
| 2 | Four Design Principles | Map spec principles to concrete implementation choices |
| 3 | Capability Negotiation | Show the handshake that makes everything discoverable |
| 4 | Server Isolation | Show the security payoff — servers only see parameters |
| 5 | Layered Architecture | Show how concerns are separated in code |
| 6 | The Tool Pattern | Show the repeatable three-move shape |
| 7 | The Safety Layer | Show defense-in-depth for writes |
| 8 | Observability | Show where logs go and why |
| 9 | Design Decisions | Show the opinionated choices as a table |
| 10 | Anti-Patterns | Show what to avoid |
| 11 | Summary | Tie it all back to the spec |

---

## References

- [MCP Architecture Specification (2026-07-28)](https://modelcontextprotocol.io/specification/2026-07-28/architecture)
- [MCP Specification Overview (2026-07-28)](https://modelcontextprotocol.io/specification/2026-07-28)
- [MCP Client Concepts](https://modelcontextprotocol.io/docs/draft/learn/client-concepts)
- [Google Dev Blog: Stateless MCP Updates](https://developers.googleblog.com/scaling-ai-agent-infrastructure-with-the-mcp-stateless-updates/)
- wxcc-mcp-server source: `wxcc-mcp-server/src/wxcc_mcp/`
