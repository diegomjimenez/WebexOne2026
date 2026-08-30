# Build a Webex MCP server

A hands-on lab. By the end you will have written a server that lets an AI
assistant manage Webex Contact Center address books — list them, create them,
and fill them with contacts — and you will understand every line of it.

The whole lab lives in one domain: **address books.** Every MCP idea — tools,
resources, prompts, and the modular shape a real server takes — is taught with
that single API. One domain, one set of credentials, one mental model, start to
finish.

---

## Before anything else: how this lab works

**Every step is a complete, standalone program.** There are seven of them:

```
webex-mcp-lab/
    mcp_servers/
        01_hello_mcp.py               the smallest server (no network, no token)
        01_hello_mcp_protocol_log.py  same server, with deprecated ctx.log()
        02_list_books.py              first real Contact Center call
        03_list_entries.py            id chaining: use a book id to list entries
        04_write_books.py             writing: create a book, add contacts
        05_resource.py                the second primitive: a resource
        06_prompt.py                  the third primitive: a prompt
        07_modular/                   the same server, built to grow
        _check.py                     quick credential check helper
    mcp_clients/
        01_hello_mcp_client.py        test client for 01 (no credentials needed)
        02_list_books_client.py       test client for 02
        03_list_entries_client.py     test client for 03 (chains book id)
        04_write_books_client.py      test client for 04
        05_resource_client.py         test client for 05
        06_prompt_client.py           test client for 06
        run_client.py                 small shared runner used by every client
        _verbose.py                   advanced: JSON-RPC frame tap for --verbose
    lab-guide/                        this guide and screenshots
    .env                              your credentials (git-ignored)
    requirements.txt                  pip dependencies
```

Each server runs on its own. `05_resource.py` does not import `02_list_books.py`,
and none of them import a shared helper module. That means a step never breaks
because you skipped the one before it — each chapter carries a full copy of the
tools it has reached so far.

**Arrived late?** Good news: you have missed nothing you cannot recover in two
minutes. Do the setup chapter below, then open whichever file the room is
currently on and run it. The earlier steps are still there when you want them,
and reading them afterwards costs nothing — each stands completely alone.

The repetition between files is on purpose. Each one is meant to be read from
top to bottom without following an import anywhere else.

---

## Setup

You need two things: Python 3.10 or newer, and — from chapter 02 onward — access
to a Webex **Contact Center** organization. Chapter 01 needs neither a token nor
a network.

> **Read this before you start.** Every chapter except 01 talks to Webex Contact
> Center. If you do not have a Contact Center organization and a token with the
> `cjp:config_read` and `cjp:config_write` scopes, you can still do chapter 01,
> but 02–07 will refuse to start and tell you which credential is missing. Decide
> now which path you are on so you are not surprised later.

### 1. Create and activate a virtual environment

From the lab folder, make an isolated environment for the lab's dependencies:

**Windows (PowerShell)**

```powershell
cd webex-mcp-lab
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS and Linux**

```bash
cd webex-mcp-lab
python3 -m venv .venv
source .venv/bin/activate
```

Your prompt now shows `(.venv)`. Activate it again in every new terminal you
open for this lab.

### 2. Install dependencies

```
pip install -r requirements.txt
```

That installs three packages into `.venv`: `mcp`, `httpx`, and `python-dotenv`.
The first two do the work. The third loads your credentials from `.env` at
startup, so no `--env-file` flag is ever needed.

### 3. Get your Contact Center credentials

You need three values:

- **A Webex access token** with the `cjp:config_read` and `cjp:config_write`
  scopes. Get a personal token from
  **https://developer.webex.com/docs/getting-started** (valid 12 hours), or
  create a bot at **https://developer.webex.com/my-apps**. The token must belong
  to an account with Contact Center configuration access.
- **Your Contact Center organization id** (`WEBEX_ORG_ID`).
- **Your Contact Center Config API base URL** (`WXCC_CONFIG_API_BASE`) — the data
  centre you belong to, e.g. `https://api.wxcc-us1.cisco.com` (or `eu1`, `anz1`, …).

### 4. Put the credentials in a file

Copy the example file and paste your values in:

**Windows (PowerShell)**

```powershell
Copy-Item .env.example .env
notepad .env
```

**macOS and Linux**

```bash
cp .env.example .env
nano .env
```

Fill in all three lines:

```
WEBEX_ACCESS_TOKEN=your-token-here
WEBEX_ORG_ID=your-org-id
WXCC_CONFIG_API_BASE=https://api.wxcc-us1.cisco.com
```

`.env` is listed in `.gitignore`. Do not commit it, and do not paste your token
into a chat window or a screenshot.

### 5. Check it works

```
python mcp_servers/01_hello_mcp.py
```

It prints one line — `webex-mcp-lab-01 running on stdio ...` — and then appears
to hang. **That is correct.** The banner goes to stderr; the server then waits
on stdin/stdout for a client to connect, so there is nothing more to print until
one does. Press `Ctrl+C` to stop it. Chapter 01 needs no credentials, so this
works even before you have filled in `.env`.

### What you need for which chapter

| Chapter | What you need |
|---|---|
| 01 | Nothing. No token, no network. |
| 02 – 07 | A Webex **Contact Center** organization, a token with the `cjp:config_read` and `cjp:config_write` scopes, plus `WEBEX_ORG_ID` and `WXCC_CONFIG_API_BASE` in your `.env`. |

**If you do not have a Contact Center organization, you can still complete
chapter 01** and read the rest. Every other chapter needs the credentials above,
and each one names the missing variable at startup rather than failing later
with an opaque HTTP error.

---

## Connecting a client

A server with no client does nothing. You need an MCP host — the application
that starts your server, shows you its tools, and asks for your approval before
anything is called.

This lab uses two, and you only need one of them.

### Visual Studio Code

Create `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "webex-mcp-lab": {
      "command": "/absolute/path/to/webex-mcp-lab/.venv/Scripts/python.exe",
      "args": ["mcp_servers/01_hello_mcp.py"],
      "cwd": "/absolute/path/to/webex-mcp-lab"
    }
  }
}
```

Point `command` at the Python interpreter inside your `.venv`, and set `cwd` to
the lab folder so the server finds your `.env`. On macOS and Linux the
interpreter is `.venv/bin/python` instead of `.venv/Scripts/python.exe`.

Replace both paths with your own, and change the script name as you work through
the chapters (for the modular finale, point `args` at `mcp_servers/07_modular/server.py`).
Use forward slashes on every platform, including Windows. No environment-file
flag is needed — the server loads `.env` itself.

![Visual Studio Code showing the webex-mcp-lab server connected, with the greet tool listed in the tool picker](images/00-vscode-connected-vscode.png)

### The Webex bot client

The alternative host is a small MCP client that runs inside a Webex bot, so the
conversation with your server happens in a Webex space. Configuration is the
same shape — a command, its arguments, and the environment.

![The Webex bot MCP client listing the tools offered by the lab server inside a Webex space](images/00-bot-connected-webexbot.png)

---

## Chapter 01 — the smallest server that works

**File: `mcp_servers/01_hello_mcp.py`**

No Webex, no network, no token. One question: what does it take to make a
Python function callable by an AI assistant?

The answer is three lines.

```python
mcp = MCPServer("webex-mcp-lab-01")


@mcp.tool()
async def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}. Your first MCP tool just ran."
```

The decorator does three separate jobs, and it is worth separating them:

1. **Discovery.** The client learns there is a tool called `greet`.
2. **Description.** The docstring becomes the tool's description. This is not
   documentation for you — it is how the model decides whether this is the
   right tool to call. A vague docstring produces a tool the model misuses.
3. **Schema.** The `name: str` annotation becomes the input schema, so the
   client knows to send one string argument.

> **A note if you search for help.** Most MCP tutorials you will find say
> `from mcp.server.fastmcp import FastMCP`. That class was renamed `MCPServer`
> and moved to `mcp.server` in version 2 of the SDK. If you paste older code
> and get `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`, this is
> why.

Chapter 01 already uses the same logging as the rest of the lab — every tool
call writes a DEBUG line to stderr. The host displays it and nothing is written
to disk. The full explanation is in chapter 02.

Ask your client: *"greet Diego"*.

![The assistant calling the greet tool and returning the greeting]()

### Try it from the command line

The test client starts the server for you, calls the tool, and shows you the
result — no VS Code or bot needed, no credentials either:

```
python mcp_clients/01_hello_mcp_client.py
```

Add `--verbose` to see every JSON-RPC message flowing between client and server.
This is the protocol that VS Code hides behind its UI — `initialize`,
`tools/list`, `tools/call`, and their responses:

```
python mcp_clients/01_hello_mcp_client.py --verbose
```

```
  CLIENT -> {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"mcp","version":"0.1.0"},"_meta":{}}}
  SERVER -> {"jsonrpc":"2.0","id":1,"result":{"capabilities":{"experimental":{},"prompts":{"listChanged":false},"resources":{"listChanged":false,"subscribe":false},"tools":{"listChanged":false}},"protocolVersion":"2025-11-25","serverInfo":{"name":"webex-mcp-lab-01","version":""}}}

-- Tools ---------------------------------------------------
  CLIENT -> {"jsonrpc":"2.0","method":"notifications/initialized"}
  CLIENT -> {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"_meta":{}}}
  SERVER -> {"jsonrpc":"2.0","id":2,"result":{"tools":[{"description":"Greet someone by name.\n\nThree things happen because of the decorator above:\n\n1. The client discovers a tool called `greet`.\n2. This docstring becomes the tool's description - it is how the model\n   decides whether this tool is the right one to call.\n3. The `name: str` annotation becomes the tool's input schema, so the\n   client knows to send one string argument.\n\nThat is the whole idea. A tool is a function the model is allowed to call.\n","inputSchema":{"properties":{"name":{"title":"Name","type":"string"}},"required":["name"],"type":"object","title":"greetArguments"},"name":"greet","outputSchema":{"properties":{"result":{"title":"Result","type":"string"}},"required":["result"],"type":"object","title":"greetOutput"}}]}}
  greet: Greet someone by name.

Three things happen because of the decorator above:

1.

-- Call: greet ---------------------------------------------
  CLIENT -> {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"greet","arguments":{"name":"Lab"},"_meta":{}}}
  SERVER -> {"jsonrpc":"2.0","id":3,"result":{"content":[{"text":"Hello, Lab. Your first MCP tool just ran.","type":"text"}],"isError":false,"structuredContent":{"result":"Hello, Lab. Your first MCP tool just ran."}}}
  Hello, Lab. Your first MCP tool just ran.
  ```


---

## Chapter 02 — the first real Webex call: list address books

**File: `mcp_servers/02_list_books.py`**

Now the tool talks to Webex Contact Center and hands back a real collection: the
address books configured in your organization.

Two things arrive in this step. The first is the credential check, done once at
startup and naming any variable that is missing:

```python
for _name, _value in (
    ("WEBEX_ACCESS_TOKEN", TOKEN),
    ("WEBEX_ORG_ID", ORG_ID),
    ("WXCC_CONFIG_API_BASE", CONFIG_API_BASE),
):
    if not _value:
        sys.exit(f"{_name} is not set. This lab needs Webex Contact Center - see .env.example.")
```

Checking at startup rather than inside the tool is deliberate. A server that
starts fine and then fails on every call is diagnosed by reading HTTP status
codes. A server that refuses to start and names the missing variable is
diagnosed by reading one line.

The second is the shape of the result:

```python
books = [
    {"id": book.get("id"), "name": book.get("name"), "description": book.get("description")}
    for book in response.json().get("data", [])
]
return {"count": len(books), "address_books": books}
```

Webex wraps collections in a `data` key and each record has many fields. We
unwrap it and keep three, because **everything a tool returns is read by a
language model** — it becomes context the model has to process. The `id` is
there because the next chapter needs it. And the token, obviously, never appears
in the result.

Ask your client: *"list my Contact Center address books"*.

![The assistant listing address books returned by the list_address_books tool](images/02-list-books-vscode.png)

### Try it from the command line

```
python mcp_clients/02_list_books_client.py
python mcp_clients/02_list_books_client.py --verbose
```

The verbose output is the same shape as chapter 01, but now the `tools/call`
result contains real API data — the address books in your organization.

### Watching the server work

Run `mcp_servers/02_list_books.py` and call the tool, and you will see more than the banner:

```
2026-08-28 18:20:01,442 DEBUG webex: list_address_books: GET https://api.wxcc-us1.cisco.com/organization/<org>/v3/address-book
2026-08-28 18:20:01,905 DEBUG webex: list_address_books: Webex responded HTTP 200
```

Logs are configured in two lines at the top of every server:

```python
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("webex")
```

They go to **stderr only** — never stdout, which carries the MCP protocol — and
the host (VS Code, the bot, your terminal) shows them; nothing is written to
disk. The token is never logged. The same two lines sit in every chapter.

---

## Chapter 03 — id chaining: list the entries inside a book

**File: `mcp_servers/03_list_entries.py`**

Chapter 02 listed address books. Each book in the result has an `id`. This
chapter uses that id to look inside a book and list its contacts — carrying the
output of one call into the input of the next.

Nothing is written. Both tools here are pure reads. The idea is to practise
chaining before mutation enters the picture in chapter 04.

The server exposes two tools:

- `list_address_books` — the same read-only tool from chapter 02, carried
  forward so this chapter is standalone.
- `list_entries(address_book_id, search="")` — takes the `id` you got from
  listing books and returns the contacts inside that book.

Ask your client: *"list my address books, then show me the entries in the first
one"* — and watch the model carry the id from the first call into the second.

### Try it from the command line

```
python mcp_clients/03_list_entries_client.py
python mcp_clients/03_list_entries_client.py --verbose
```

The client does the chaining for you: it calls `list_address_books`, takes the
first book's id, and passes it to `list_entries`. In verbose mode you see two
`tools/call` frames on the wire, the second carrying the id from the first
response — chaining made visible at the protocol level.

If your organization has no address books yet, the client reports there is
nothing to chain and exits cleanly.

---

## Chapter 04 — writing: create a book, then fill it

**File: `mcp_servers/04_write_books.py`**

Everything so far only read. This chapter writes, and it introduces two ideas
at once.

### Who asks permission

```python
@mcp.tool()
async def create_address_book(name: str, description: str = "") -> dict:
```

Look at what is **not** in that function. There is no `confirm` argument. There
is no dry-run mode, and the server never stops to ask whether you meant it. It
creates the book.

That is not an oversight, and it is the most important idea in this lab.

**Consent belongs to the host, not to the server.** Before `create_address_book`
is entered, your MCP client shows you the tool name and its arguments and waits
for you to approve. Every MCP host does this. It is part of the protocol's
design, not a feature of any particular server.

![The Visual Studio Code approval prompt showing the create_address_book tool with its arguments, waiting for the user to allow or deny](images/03-approval-vscode.png)

So a server that builds its own approval step is not adding safety. It is adding
a second dialog in front of the first one, and teaching its users that clicking
through dialogs is normal. The host already asked. Trust it, and keep your tool
honest about what it does.

**There are also no delete tools in this file** — not because deleting is hard,
but because address books are shared configuration on a shared organization. A
mistaken create leaves a stray book for an administrator to remove; a mistaken
delete removes a book and every contact in it. Those are not comparable, so the
verb is simply absent. Deciding which operations a tool exposes *at all* is a
more effective control than any confirmation flow.

### Chaining calls

`create_address_book` returns the new book's id; `add_entry` takes that id as
its first argument:

```python
return {"created": True, "address_book_id": book.get("id"), "name": book.get("name")}
```

```python
async def add_entry(address_book_id: str, name: str, number: str) -> dict:
```

Watch the model carry the id from the first call into the second. That is most
of what "using tools together" means, and it is why the create result puts the
id front and centre.

The other thing worth copying is the failure handling — every branch of `_fail`
returns a sentence, not an exception, so one bad call never takes the server
down and the model can relay the reason to you.

Ask your client: *"create an address book called Lab Contacts, then add Acme
Reception on +14155550101"* — and watch for the approval prompt before anything
is written.

![The assistant creating an address book and adding a contact through the Contact Center tools](images/03-write-books-vscode.png)

### Try it from the command line

```
python mcp_clients/04_write_books_client.py
python mcp_clients/04_write_books_client.py --verbose
```

The client lists all four tools but only calls `list_address_books` — it is
read-only by design, so running it cannot modify your organization. In verbose
mode, notice that `tools/list` now returns four tools instead of one.

---

## Chapter 05 — the second primitive: a resource

**File: `mcp_servers/05_resource.py`**

MCP has three primitives. You have been using one of them.

```python
@mcp.resource("webex://address-books/conventions")
def address_book_conventions() -> str:
    """House style for address books in this organization."""
```

A **tool** is an action the *model* decides to take. A **resource** is reference
material the *client* attaches to the conversation, the way you would attach a
file. Reading a resource changes nothing — that is exactly why a client can pull
one in without asking you first.

The resource here is the house style for address books: name a book for its
team, store numbers in E.164, check for a duplicate before creating one. It
exists to shape how `create_address_book` and `add_entry` get used — the write
tools' docstrings point straight at it. That is the useful pattern: a resource
is context that makes your tools behave better.

The URI is how a client refers to it. The scheme is yours to choose — `webex://`
here — and it need not correspond to anything on a network.

![The resource picker in Visual Studio Code showing the address book conventions resource offered by the server](images/04-resource-vscode.png)

### Try it from the command line

```
python mcp_clients/05_resource_client.py
python mcp_clients/05_resource_client.py --verbose
```

This is where the verbose output gets interesting. Two new JSON-RPC methods
appear for the first time: `resources/list` and `resources/read`. The client
lists all resources, reads the conventions resource, then lists tools and calls
one — so you see the full surface of a server that offers both primitives.

---

## Chapter 06 — the third primitive: a prompt

**File: `mcp_servers/06_prompt.py`**

```python
@mcp.prompt()
def set_up_address_book(book_name: str = "", team: str = "") -> str:
```

Now all three primitives are in one file, and the difference between them is
*who reaches for them*:

| Primitive | Who invokes it | What it is |
|---|---|---|
| tool | the model | an action |
| resource | the client | reference material |
| prompt | the **user** | a starting point |

A prompt is the one primitive a human triggers directly — usually from a slash
command or a menu. What it returns is not an answer. It is the opening message
of a conversation:

```python
return (
    f"Set up an address book called {book_name} for the {team} team.\n"
    "\n"
    "1. Read the webex://address-books/conventions resource and follow it.\n"
    "2. Call list_address_books first - reuse a matching book, do not duplicate.\n"
    "3. Otherwise call create_address_book and keep the id it returns.\n"
    "4. Ask me for the contacts (name and E.164 number each).\n"
    "5. Show me the list and, once I approve, call add_entry for each."
)
```

Read that as what it is: a workflow, written by the person who knows how the job
should be done, packaged so a user can trigger it without knowing any of the
steps. It orchestrates the tools *and* the resource from the two chapters
before it — the whole address-book surface, behind one menu item. The arguments
become fields the client asks the user to fill in.

![The prompt appearing as a slash command in the client, with fields for book name and team](images/05-prompt-vscode.png)

### Try it from the command line

```
python mcp_clients/06_prompt_client.py
python mcp_clients/06_prompt_client.py --verbose
```

Two more new JSON-RPC methods: `prompts/list` and `prompts/get`. The client
lists prompts, gets `set_up_address_book` with sample arguments, then lists
resources and tools — so the verbose output now shows all three MCP primitives
exercised in a single session.

---

## Chapter 07 — the same server, built to grow

**Directory: `mcp_servers/07_modular/`**

Every chapter so far put everything in one file. That is the right shape for
reading and the wrong shape for a server you keep. This chapter is the same
functionality in the shape you would actually maintain.

```
mcp_servers/07_modular/
    server.py            decides which domains are switched on
    webex_client.py      credentials and HTTP, resolved once
    tools/
        __init__.py      the contract, written down
        address_books.py the whole lab: four tools, a resource, and a prompt
        _template.py     a starting point for a second API family
```

Three kinds of file, and no more.

### One domain, every primitive

`tools/address_books.py` is a single domain module that registers **all three
primitives** — four tools, the conventions resource, and the set-up prompt. It
is the modular form of chapters 02–06, and it shows the pattern you would follow
for any subject area: one file owns one domain, top to bottom.

### The whole extension mechanism

```python
DOMAINS = [
    address_books,
]
```

That is it. **To add a subject area:** write `tools/your_domain.py` with a
`register(mcp, client)` function and add it to that list. **To switch one off:**
delete its line. Registration is an explicit list rather than a directory scan,
so you can read those lines and know precisely what the server exposes. So can a
reviewer.

### The contract, in full

A domain module is any file in `tools/` that provides:

```python
def register(mcp, client) -> None:
    ...
```

Inside it, declare tools, resources, and prompts with the usual decorators on
the `mcp` you were handed, and make HTTP calls through `client`. Two rules keep
domains independent:

- **A domain module never imports another domain module.** If two domains need
  the same helper, it belongs in `webex_client.py`.
- **A domain module never reads `os.environ`.** Ask the client instead.

Follow those and a new domain cannot break an existing one, because it cannot
reach it.

### Why credentials live in one place

`webex_client.py` is the only file that reads environment variables and the only
file that holds the token. Domain modules get a `WebexClient` and never see the
credential:

```python
self._token = self._settings.pop("WEBEX_ACCESS_TOKEN", None)
```

Because no domain module can reach the token, no tool schema, tool result, or
log line in this server can leak it — a property you can check by reading one
file rather than auditing every domain. The address book domain asks for its
extra credentials at registration time, in its own words:

```python
settings = client.require(
    "WEBEX_ORG_ID", "WXCC_CONFIG_API_BASE", needed_by="the address book domain"
)
```

so a misconfiguration is reported once, at startup, naming both the missing
variable and the domain that wanted it — rather than once per tool call, as a
403.

### One log line for every domain

In chapters 02–06 each tool wrote its own DEBUG lines; here that moves into
`webex_client.request`, which every domain already calls:

```python
log.debug("-> %s %s", method, url)
...
log.debug("<- HTTP %s (%s %s)", response.status_code, method, url)
```

Write it once and every domain is traced — including one you add tomorrow from
the template, which needs no logging code of its own. The logger is configured
once in `webex_client.py` and shared by name (`logging.getLogger("webex")`), so
`server.py` and each domain use the same stderr sink with no setup. And because
the token lives only in `WebexClient`, the request log physically cannot
contain it.

![The modular server connected, showing the address book tools, resource, and prompt in one list](images/06-modular-vscode.png)

---

## Add your own Webex API family

Chapter 07 gave you the mechanism. Here is the recipe. There is a starting point
in the tree for exactly this: `mcp_servers/07_modular/tools/_template.py`. It is a complete
domain module that does nothing yet — it is not in `DOMAINS`, and its one tool
returns placeholder data over no network — so copying it is safe and changes
nothing until you wire it in.

Five steps:

1. **Copy the template.** `tools/_template.py` → `tools/<your_domain>.py`
   (for example `calling.py` or `meetings.py`).
2. **Rename the tool** and rewrite its docstring to say what it does. The
   docstring is how the model decides whether to call it, so make it specific.
3. **Point it at an endpoint.** Replace the placeholder body with a
   `client.request(...)` call. **This is the one place the API family is
   chosen** — Webex Calling, Meetings, and other Contact Center APIs are all
   just a different URL here; the contract around it does not change.
4. **Register it.** Add your module to the `DOMAINS` list in `server.py` — one
   line, exactly as `address_books` is already listed.
5. **Restart.** Your new tool appears alongside the others.

Two notes so you are not surprised:

- **Nothing new to install or configure.** The recipe adds no dependency. A
  domain that needs extra credentials asks for them at registration time with
  `client.require(...)` — copy that shape from `address_books.py`.
- **The template tool is read-only on purpose.** For a write, copy the
  `create_address_book` or `add_entry` shape instead; for extra configuration,
  copy the `client.require(...)` line. Both live in `address_books.py`.

---

## Companion scripts and protocol observability — reference

Each chapter above has a "Try it from the command line" section that introduces
its test client. This section is a quick-reference summary and explains the
logging layers in more detail.

| Server | Client | Needs credentials? |
|---|---|---|
| `mcp_servers/01_hello_mcp.py` | `mcp_clients/01_hello_mcp_client.py` | No |
| `mcp_servers/02_list_books.py` | `mcp_clients/02_list_books_client.py` | Yes |
| `mcp_servers/03_list_entries.py` | `mcp_clients/03_list_entries_client.py` | Yes |
| `mcp_servers/04_write_books.py` | `mcp_clients/04_write_books_client.py` | Yes |
| `mcp_servers/05_resource.py` | `mcp_clients/05_resource_client.py` | Yes |
| `mcp_servers/06_prompt.py` | `mcp_clients/06_prompt_client.py` | Yes |

Every client accepts `--verbose` (`-v`) to print raw JSON-RPC frames.

The clients share a small runner in `mcp_clients/run_client.py` — it spawns the
matching server from `mcp_servers/`, connects via `mcp.Client`, and runs the
`exercise` coroutine that each numbered client file defines. When you pass
`--verbose`, `run_client.py` lazily imports `mcp_clients/_verbose.py`, which
taps the stdio streams and prints every JSON-RPC frame as `CLIENT ->` or
`SERVER ->`. `_verbose.py` is labelled advanced/optional reading: you do not
need to open it to use the clients.

### Three layers of logging

```
Layer           Where it lives      Who sees it
--------------- ------------------- ----------------------------
Python logging  stderr              you (the server operator)
ctx.log()       JSON-RPC protocol   the client (DEPRECATED)
JSON-RPC frames stdin/stdout wire   nobody, unless you intercept
```

**Python logging** is the durable approach. Every chapter uses it. It goes to
stderr only — the host displays it, and nothing is written to disk. The server
owns it; the client never sees it. This is what you should use going forward.

**`ctx.log()`** sent `notifications/message` frames to the client over the
protocol. The MCP spec retired this feature in SEP-2577 (2026-07-28): modern
servers only send log entries when the request explicitly opts in via `_meta`,
and the whole capability is being wound down. `ctx.log()` still works in today's
SDK but emits a deprecation warning.

**JSON-RPC frames** are the raw protocol itself — `initialize`, `tools/list`,
`tools/call`, and their responses. The test-client companions intercept these
when `--verbose` is on.

### `mcp_servers/01_hello_mcp_protocol_log.py` — old vs new logging

This companion mirrors `01_hello_mcp.py` but demonstrates both logging
approaches in the same tool:

```python
log.debug("greet called: name=%r", name)       # Python logging (durable)
await ctx.log("debug", f"greet called: ...")    # ctx.log (deprecated)
```

Run it the same way:

```
python mcp_servers/01_hello_mcp_protocol_log.py
```

It starts identically to `01_hello_mcp.py`. The difference only shows when
a client calls the `greet` tool: the Python log line always appears in stderr;
the `ctx.log` line only appears if the client opted in to protocol-level
logging.

### What to look for in `--verbose` output

- **The `initialize` handshake.** The client sends its capabilities, the server
  replies with its own. This is where the protocol version and server name are
  exchanged.
- **`notifications/initialized`.** The client confirms the handshake. Only after
  this can either side send requests.
- **`resources/list`, `tools/list`, `prompts/list`.** The client discovers what
  the server offers.
- **`tools/call`.** The actual work. If credentials are missing, the server exits
  before the handshake completes and the client prints a message explaining why.

> **Note:** Clients 02–06 require the same `.env` credentials as the servers
> they spawn (Contact Center access). Without credentials the server exits at
> startup and the client reports the connection closed early. Client 01 needs
> no credentials — it is the ideal first test.

---

## Where to go next

You now have a server you can extend. The obvious next moves:

- **Add a domain.** Contact Center has far more than address books — queues,
  teams, users, skills — and the contract is the same four lines.
- **Read your tool descriptions as the model does.** They are the interface.
  Most tools that behave badly are described badly.
- **Watch what you return.** Every field is context. Trim.

---

## Contributor notes

### Screenshots

Images live in `lab-guide/images/` and are referenced with repository-relative
paths so the guide renders offline.

Filenames follow `NN-<slug>-<client>.png`:

- `NN` — the chapter number the image belongs to, `00` for setup chapters
- `<slug>` — what the image shows, in words (`approval`, `list-books`, `modular`)
- `<client>` — the host it was captured in: `vscode` or `webexbot`

Every image needs alternative text describing what is on screen, not just
naming it. `![The Visual Studio Code approval prompt showing the
create_address_book tool with its arguments](...)` — not `![screenshot](...)`.

Before committing an image, check that no access token, client secret, or
organization identifier is legible anywhere in the frame, including window
titles, terminal scrollback, and browser tabs.
