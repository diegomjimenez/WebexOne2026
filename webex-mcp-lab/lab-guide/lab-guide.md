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

**Every step is a complete, standalone program.** There are six of them (plus a modular variant):

```
webex-mcp-lab/
    mcp_servers/
        01_hello_mcp.py                  the smallest server (no network, no token)
        01_hello_mcp_protocol_log.py     same server, with deprecated ctx.log()
        02_hello_resource_prompt.py      all three primitives (no network, no token)
        03_read_books.py                 reading: list address books, list entries
        04_write_books.py                writing: create a book, add contacts
        05_delete_books.py               deleting: remove a book or entry (elicitation)
        06_full_server.py                capstone: prompt + resource + tools on the API
        07_modular/                      the same server, built to grow
    lab-guide/                           this guide and screenshots
    .env                                 your credentials (git-ignored)
    requirements.txt                     pip dependencies
```

Each server runs on its own. `05_delete_books.py` does not import
`03_read_books.py`, and none of them import a shared helper module. That means
a step never breaks because you skipped the one before it.

**Arrived late?** Good news: you have missed nothing you cannot recover in two
minutes. Do the setup chapter below, then open whichever file the room is
currently on and run it. The earlier steps are still there when you want them,
and reading them afterwards costs nothing — each stands completely alone.

The repetition between files is on purpose. Each one is meant to be read from
top to bottom without following an import anywhere else.

---

## Setup

You need two things: Python 3.10 or newer, and — from chapter 03 onward — access
to a Webex **Contact Center** organization. Chapters 01–02 need neither a token
nor a network.


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
one does. Press `Ctrl+C` to stop it. Chapters 01–02 need no credentials, so
this works even before you have filled in `.env`.

### What you need for which chapter

| Chapter | What you need |
|---|---|
| 01 – 02 | Nothing. No token, no network. |
| 03 – 06 | A Webex **Contact Center** organization, a token with the `cjp:config_read` and `cjp:config_write` scopes, plus `WEBEX_ORG_ID` and `WXCC_CONFIG_API_BASE` in your `.env`. |

**If you do not have a Contact Center organization, you can still complete
chapters 01–02** and read the rest. Those two chapters teach every MCP
primitive without a network. Every other chapter needs the credentials above,
and each one names the missing variable at startup rather than failing later
with an opaque HTTP error.

---

## Connecting a client

A server with no client does nothing. You need an MCP host — the application
that starts your server, shows you its tools, and asks for your approval before
anything is called.

This lab recommends **VS Code with your own OpenAI key** (BYOK). It supports
every MCP primitive — tools, resources, and prompts — without a GitHub account
or Copilot subscription. You only need an OpenAI API key.

### VS Code with Bring Your Own Key (recommended)

**Requirements:** VS Code 1.122 or newer, and an OpenAI API key.

**Step 1 — Add your OpenAI model.** Open the Command Palette
(`Ctrl+Shift+P` / `Cmd+Shift+P`) and run **Chat: Manage Language Models**.
Click **Add Models**, select **OpenAI**, paste your API key, and pick a model
(e.g. `gpt-4o`). The Chat view appears immediately — no GitHub sign-in needed.

> **First-time note.** VS Code may ask you to assign a model for utility tasks
> (title generation, etc.). Point it at the same `gpt-4o` model — this is a
> one-time prompt.

**Step 2 — Register the MCP server.** Create `.vscode/mcp.json` in the lab
workspace:

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
the chapters (for the modular finale, point `args` at
`mcp_servers/07_modular/server.py`). Use forward slashes on every platform,
including Windows. No environment-file flag is needed — the server loads `.env`
itself.

**Step 3 — Use it.** Open the Chat view and ask:
*"clean the number (415) 555-0101"*. VS Code starts the server, discovers
`format_phone`, and asks for your approval before calling it.

**How to access each MCP primitive in VS Code:**

| Primitive | How to access |
|---|---|
| **Tools** | Just ask in chat — the model discovers and calls them automatically |
| **Resources** | Click **Add Context** > **MCP Resources** in the Chat view |
| **Prompts** | Type `/. ` (slash-dot-space) in the chat input to see available prompts |

![Visual Studio Code showing the webex-mcp-lab server connected, with the format_phone tool listed in the tool picker]

### Codex CLI (alternative — tools only)

OpenAI Codex CLI works as an alternative client, but **it only supports tools**.
Resources and prompts are not available in Codex — chapters 02 and 03 cannot be
fully demonstrated with this client.

Install and authenticate from the VS Code terminal:

```powershell
npm install -g @openai/codex
$env:OPENAI_API_KEY = "sk-your-real-key-here"
Write-Output $env:OPENAI_API_KEY | codex login --with-api-key
codex login status
```

Type your real key directly in the terminal; do not add it to this guide, source
control, or `.vscode/mcp.json`.

Codex does not read `.vscode/mcp.json`. Register the server in
`C:/Users/<you>/.codex/config.toml`:

```toml
[mcp_servers.webex-mcp-lab]
command = "C:/absolute/path/to/webex-mcp-lab/.venv/Scripts/python.exe"
args = ["mcp_servers/01_hello_mcp.py"]
cwd = "C:/absolute/path/to/webex-mcp-lab"
```

Replace the paths, then verify and start:

```powershell
codex mcp list
codex
```

Ask Codex to `use MCP to clean the number (415) 555-0101`. It starts the
server, discovers `format_phone`, and asks for approval before calling it.

### Which client supports what

| | VS Code BYOK | Codex CLI | MCP Inspector |
|---|---|---|---|
| **Tools** | yes | yes | yes |
| **Resources** | Add Context menu | discoverable, model may skip | click to read |
| **Prompts** | `/. ` slash commands | **not supported** | Prompts tab |
| **Best for** | chapters 01–06 | chapters 01, 03–06 | any chapter (debug) |

---

## Chapter 01 — the smallest server that works

**File: `mcp_servers/01_hello_mcp.py`**

No Webex, no network, no token. One question: what does it take to make a
Python function callable by an AI assistant?

The answer is a decorator on a real function. Here is the whole tool:

```python
import re

@mcp.tool()
async def format_phone(number: str) -> str:
    """Clean a phone number to E.164 form, e.g. +14155550101."""
    digits = re.sub(r"\D", "", number)
    if not number.startswith("+") and len(digits) == 10:
        digits = "1" + digits
    return "+" + digits
```

Everything a `@mcp.tool()` decorator does is on display here:

1. **Discovery.** The client learns there is a tool called `format_phone`.
2. **Description.** The docstring becomes the tool's description. This is not
   documentation for you — it is how the model decides whether this is the
   right tool to call. A vague or misleading docstring produces a tool the
   model misuses.
3. **Schema.** The `number: str` annotation becomes the input schema, so the
   client knows to send one string argument.

And the *body* does real work: strip everything that is not a digit
(`re.sub(r"\D", "", ...)`), assume the US country code when the caller gave
ten digits and no `+`, then return the result in E.164 form. Predictable,
deterministic, and something a language model would not reliably get right
on its own. That is the whole point of a tool.

> **Why the assumption `+1`?** This lab targets a Contact Center audience
> that mostly enters US numbers. It is a chapter-01 shortcut, called out in
> chapter 02's resource. The exercises below invite you to change it.

**Ask your client:** *"clean the number (415) 555-0101"*. It calls
`format_phone`, the server strips the punctuation, and returns
`+14155550101` back to the assistant, which shows it to you.

> **A note if you search for help.** Most MCP tutorials say
> `from mcp.server.fastmcp import FastMCP`. That class was renamed `MCPServer`
> and moved to `mcp.server` in version 2 of the SDK. If you paste older code
> and get `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`, this
> is why.

### Exercise: change what the assistant knows about `format_phone`

The docstring is the description sent to the MCP client. Change it in
`mcp_servers/01_hello_mcp.py` from:

```python
"""Clean a phone number to E.164 form, e.g. +14155550101."""
```

to something more specific, for example:

```python
"""Normalize a US phone number to E.164 for Contact Center use."""
```

Run the client again:

```powershell
python mcp_clients/01_hello_mcp_client.py
```

Compare the line under `-- Tools --` before and after your edit. The
function body did not change, so cleaning the same number still returns the
same string. Only the assistant's understanding of *when to reach for the
tool* changed.

### Exercise: change what `format_phone` does

Change the body of the function. For example, default to `+44` instead of
`+1`, or refuse to prepend a country code at all and return `"+" + digits`
regardless. Run the client again and see the result under `-- Call:
format_phone --` change. The description tells the assistant when a tool
might be useful; the function body determines what happens after the
assistant calls it.

### Try it from the command line

The test client starts the server for you, calls the tool, and shows you
the result — no VS Code or bot needed, no credentials either:

```
python mcp_clients/01_hello_mcp_client.py
```

Add `--verbose` to see every JSON-RPC message flowing between client and
server. This is the protocol that VS Code hides behind its UI —
`initialize`, `tools/list`, `tools/call`, and their responses:

```
python mcp_clients/01_hello_mcp_client.py --verbose
```

![verbose output showing the initialize handshake, tools/list, and tools/call frames](C:\WorkRelated_LocalFiles\wx1Simple\WebexOne2026\webex-mcp-lab\lab-guide\images\verbose1.png)





### Inspect every server with MCP Inspector

MCP Inspector is a browser-based MCP client for exploring a server's tools,
resources, prompts, and raw protocol messages. It is useful while building each
chapter because it shows exactly what the server advertises, without involving
an AI assistant.

Install Node.js first if `npx` is not already available. From the lab root, run
Inspector with the virtual-environment Python interpreter followed by the server
script you want to inspect:

```powershell
npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/01_hello_mcp.py
```

Open the Inspector URL printed in the terminal, choose the **STDIO** transport,
and click **Connect**. Use its Tools, Resources, Prompts, and Notifications
tabs to explore the server. Select `format_phone` in Tools, enter a `number`
value, and run it to see the result and its server log messages.

Stop Inspector with `Ctrl+C`, then replace the final argument with the server
for the chapter you are working on:

| Chapter | Inspector command |
|---|---|
| 01 | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/01_hello_mcp.py` |
| 01 logging | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/01_hello_mcp_protocol_log.py` |
| 02 | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/02_hello_resource_prompt.py` |
| 03 | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/03_read_books.py` |
| 04 | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/04_write_books.py` |
| 05 | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/05_delete_books.py` |
| 06 | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/06_full_server.py` |
| 07m | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/07_modular/server.py` |

Chapters 01–02 and the logging companion need no credentials. Chapters 03-06 load
the same `.env` file used by the other clients, so fill in the Webex Contact
Center credentials before connecting. On macOS or Linux, replace
`.venv/Scripts/python.exe` with `.venv/bin/python`.

---

## Chapter 02 — all three primitives, no network

**File: `mcp_servers/02_hello_resource_prompt.py`**

Still no Webex, still no credentials. This chapter puts all three MCP
primitives — tool, resource, and prompt — into one short file, using a
word-count example that has nothing to do with phones.

```python
@mcp.tool()
async def count_words(text: str) -> dict:
    """Count the words and characters in a piece of text."""
    words = text.split()
    return {"words": len(words), "characters": len(text)}
```

A tool is an action the model calls. `count_words` counts — that is all it
knows. It has no idea what the limits should be, or which words are banned.

```python
@mcp.resource("lab://greeting-rules")
def greeting_rules() -> str:
    return (
        "Rules for agent chat greetings:\n"
        "1. 12 words maximum.\n"
        "2. Must include the agent's first name.\n"
        "3. Never use 'ASAP' or 'obviously'.\n"
    )
```

A resource is context the client attaches, like handing the model a
rulebook. **The tool cannot know these rules.** `count_words` returns 7
for any 7-word text; only the resource says the limit is 12 and "ASAP" is
banned. That is why a resource matters: it carries rules the tool itself
does not encode.

```python
@mcp.prompt()
def review_greeting(greeting: str = "") -> str:
    return (
        f"Review this agent greeting:\n\n"
        f"{greeting or '<paste a greeting here>'}\n\n"
        "1. Read the lab://greeting-rules resource for the org rules.\n"
        "2. Call count_words to measure the greeting.\n"
        "3. Tell me pass or fail, and why."
    )
```

A prompt is the one primitive a human triggers directly — from a slash
command or menu. It returns the opening message the model sees, wiring the
resource and the tool into a single review workflow.

### The three primitives, side by side

| Primitive | Who invokes it | What it is | Example |
|---|---|---|---|
| tool | the model | an action | `count_words(text)` |
| resource | the client | policy / reference material | `lab://greeting-rules` |
| prompt | the **user** | a starting point | `review_greeting(greeting)` |

### The A/B test

Try the same question — *"is this greeting OK: Hi, I'm Sam — how can I
help you today?"* — with and without the resource attached:

|  | Without `lab://greeting-rules` | With `lab://greeting-rules` |
|---|---|---|
| What the model checks | invents its own standards | applies the 12-word max, first-name rule, and banned words |
| Adding "ASAP" to the greeting | model probably accepts it | model flags the banned word |

> **In VS Code:** Click **Add Context** > **MCP Resources** and select
> `lab://greeting-rules`. Or type `/. ` to invoke `review_greeting` from
> the prompt menu.

---

## Chapter 03 — the first real Webex call: read address books

**File: `mcp_servers/03_read_books.py`**

Now the tool talks to Webex Contact Center. This chapter exposes two read-only
tools: `list_address_books` and `list_entries`.

The credential check runs once at startup and names any variable that is missing:

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
refuses to start and names the missing variable is diagnosed by reading one
line. A server that starts fine and then fails on every call requires HTTP
status codes.

### Shaping what the model sees

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
there because later chapters need it. And the token, obviously, never appears
in the result.

### Id chaining

Each book in the result has an `id`. `list_entries(address_book_id)` takes
that id and returns the contacts inside that book — carrying the output of
one call into the input of the next. Ask your client: *"list my address
books, then show me the entries in the first one"* — and watch the model
chain the id from the first call into the second.

---

## Chapter 04 — writing: create a book, then fill it

**File: `mcp_servers/04_write_books.py`**

This chapter writes. It exposes exactly two tools: `create_address_book` and
`add_entry`. There are no read tools here — listing is chapter 03's job.

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

### Chaining calls

`create_address_book` returns the new book's id; `add_entry` takes that id as
its first argument:

```python
return {"created": True, "address_book_id": book.get("id"), "name": book.get("name")}
```

```python
async def add_entry(address_book_id: str, name: str, number: str) -> dict:
```

Watch the model carry the id from the first call into the second. The create
result puts the id front and centre precisely so the next tool can use it.

The other thing worth copying is the failure handling — every branch of `_fail`
returns a sentence, not an exception, so one bad call never takes the server
down and the model can relay the reason to you.

Ask your client: *"create an address book called Lab Contacts, then add Acme
Reception on +14155550101"* — and watch for the approval prompt before anything
is written.

---

## Chapter 05 — deleting with a safety net: elicitation

**File: `mcp_servers/05_delete_books.py`**

Chapter 04 trusted the host to ask permission. This chapter explores what
happens when the server itself needs to ask a question mid-call. The MCP
protocol calls this **elicitation**: the server pauses, sends a form to the
user, and resumes based on the answer.

The server exposes exactly two tools: `delete_address_book` and `delete_entry`.
There are no read tools — the id to delete comes from the **create → fill →
delete** narrative. You already have a fresh id in the transcript from chapters
03 and 04.

> **Tip:** If you want to list address books alongside deletion, register
> `03_read_books.py` and `05_delete_books.py` as two separate MCP servers in
> your client. One server lists, the other deletes.

### The resolver pattern

```python
class Confirm(BaseModel):
    ok: bool

async def confirm_delete_book(address_book_id: str) -> Elicit[Confirm]:
    return Elicit(f"Delete address book '{address_book_id}'? This cannot be undone.", Confirm)
```

The resolver runs **before** the tool body. The user sees a form with one
boolean field. Three outcomes are possible:

| Outcome | What happens |
|---|---|
| `AcceptedElicitation(ok=True)` | DELETE fires, item is removed |
| `AcceptedElicitation(ok=False)` | User said "no" — tool body skips the HTTP call |
| `DeclinedElicitation` / `CancelledElicitation` | User dismissed — tool body skips the HTTP call |

This is different from the host's built-in approval. The host asks *"should I
call this tool at all?"*. Elicitation asks *"I am inside the tool — are you
sure about this specific action?"*. The two are complementary.

---

## Chapter 06 — capstone: prompt + resource + tools on the real API

**File: `mcp_servers/06_full_server.py`**

Every primitive you have learned — tool, resource, prompt, and elicitation —
cooperates in one file, on the real Contact Center API. The capstone registers:

- **One prompt** (`set_up_address_book`) — a workflow that orchestrates
  everything below.
- **One resource** (`lab://address-books`) — the house style guide that shapes
  how the tools are used.
- **Five tools** — `list_address_books`, `create_address_book`, `add_entry`,
  `delete_address_book`, and `delete_entry`.

### File-only logging

Unlike every other chapter, the capstone does **not** log to stderr. Debug
output goes exclusively to a file:

```
mcp_servers/07_full_server.log
```

Open this file after each run to see every prompt invocation, resource read,
outbound HTTP request, and response status. The log appends across runs, so
you build up a history of what the model did. Delete the file when it gets
unwieldy — it is git-ignored.

> **Why not stderr?** The capstone produces a lot of debug traffic (five tools
> times multiple HTTP calls). Writing it to a file keeps the terminal clean
> while still giving you full observability after the fact.

Ask your client: *"set up an address book called Lab Contacts for the support
team"* — then open `mcp_servers/07_full_server.log` to see everything the
server did.

---

## Chapter 07m — the same server, built to grow

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
is the modular form of chapters 03–06, and it shows the pattern you would follow
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

In chapters 03–06 each tool wrote its own DEBUG lines; here that moves into
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

Chapter 06 gave you the mechanism. Here is the recipe. There is a starting point
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

| Server | Needs credentials? |
|---|---|
| `mcp_servers/01_hello_mcp.py` | No |
| `mcp_servers/02_hello_resource_prompt.py` | No |
| `mcp_servers/03_read_books.py` | Yes |
| `mcp_servers/04_write_books.py` | Yes |
| `mcp_servers/05_delete_books.py` | Yes |
| `mcp_servers/06_full_server.py` | Yes |

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

This companion demonstrates both logging approaches side by side in the same
tool:

```python
log.debug("tool called: arg=%r", arg)       # Python logging (durable)
await ctx.log("debug", f"tool called: ...") # ctx.log (deprecated)
```

Run it the same way:

```
python mcp_servers/01_hello_mcp_protocol_log.py
```

It starts identically to `01_hello_mcp.py`. The difference only shows when a
client calls its tool: the Python log line always appears in stderr; the
`ctx.log` line only appears if the client opted in to protocol-level
logging.

> **Note:** the protocol-log companion is a legacy demo and still uses the
> lab's original example tool; the mechanism it illustrates (`log.debug` vs.
> `ctx.log`) is what matters, not the tool name.

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

> **Note:** Clients 04–06 require the same `.env` credentials as the servers
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
