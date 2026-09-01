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

**Every step is a complete, standalone program.** There are eight of them:

```
webex-mcp-lab/
    mcp_servers/
        01_hello_mcp.py               the smallest server (no network, no token)
        01_hello_mcp_protocol_log.py  same server, with deprecated ctx.log()
        02_hello_resource.py          adds a resource: org phone policy (no network)
        03_hello_prompt.py            adds a prompt: apply the policy to a list (no network)
        04_list_books.py              first real Contact Center call
        05_list_entries.py            id chaining: use a book id to list entries
        06_write_books.py             writing: create a book, add contacts
        07_full_server.py             capstone: prompt + resource + tools on the API
        07_modular/                   the same server, built to grow
        _check.py                     quick credential check helper
    mcp_clients/
        01_hello_mcp_client.py        test client for 01 (no credentials needed)
        02_hello_resource_client.py   test client for 02 (no credentials needed)
        03_hello_prompt_client.py     test client for 03 (no credentials needed)
        04_list_books_client.py       test client for 04
        05_list_entries_client.py     test client for 05 (chains book id)
        06_write_books_client.py      test client for 06
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

You need two things: Python 3.10 or newer, and — from chapter 04 onward — access
to a Webex **Contact Center** organization. Chapters 01–03 need neither a token
nor a network.


!!!!!!!!
do we really neeed this below ??
!!!!!!!!


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


!!!!!!!!
do we really neeed the above??
!!!!!!!!


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
one does. Press `Ctrl+C` to stop it. Chapters 01–03 need no credentials, so
this works even before you have filled in `.env`.

### What you need for which chapter

| Chapter | What you need |
|---|---|
| 01 – 03 | Nothing. No token, no network. |
| 04 – 07 | A Webex **Contact Center** organization, a token with the `cjp:config_read` and `cjp:config_write` scopes, plus `WEBEX_ORG_ID` and `WXCC_CONFIG_API_BASE` in your `.env`. |

**If you do not have a Contact Center organization, you can still complete
chapters 01–03** and read the rest. Those three chapters teach every MCP
primitive without a network. Every other chapter needs the credentials above,
and each one names the missing variable at startup rather than failing later
with an opaque HTTP error.

---

## Connecting a client

A server with no client does nothing. You need an MCP host — the application
that starts your server, shows you its tools, and asks for your approval before
anything is called.

This lab uses two, and you only need one of them.

!!!!
vs code could be removed
!!!!!


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

![Visual Studio Code showing the webex-mcp-lab server connected, with the format_phone tool listed in the tool picker]

### Codex CLI in Visual Studio Code

You can also run OpenAI Codex CLI from the integrated terminal in Visual Studio
Code. Install it, then authenticate with your OpenAI API key:

```powershell
npm install -g @openai/codex
$env:OPENAI_API_KEY = "sk-your-real-key-here"
Write-Output $env:OPENAI_API_KEY | codex login --with-api-key
codex login status
```

Type your real key directly in the terminal; do not add it to this guide, source
control, or `.vscode/mcp.json`. `codex login status` should report that you are
logged in using an API key.

Codex is separate from the VS Code MCP host and does not read
`.vscode/mcp.json`. Register the server in `C:/Users/<you>/.codex/config.toml`:
This is from dcloud -> C:\Users\Administrator.DCLOUD\.codex\config.toml

```toml
[mcp_servers.webex-mcp-lab]
command = "C:/absolute/path/to/webex-mcp-lab/.venv/Scripts/python.exe"
args = ["mcp_servers/01_hello_mcp.py"]
cwd = "C:/absolute/path/to/webex-mcp-lab"
```

![toml](C:\WorkRelated_LocalFiles\wx1Simple\WebexOne2026\webex-mcp-lab\lab-guide\images\config.toml.png)


example 
```
[mcp_servers.webex-mcp-lab]
enabled = true
command = "C:/WebexOne/31.08.2026/WebexOne2026/webex-mcp-lab/.venv/Scripts/python.exe"
args = ["01_hello_mcp.py"]
cwd = "C:/WebexOne/31.08.2026/WebexOne2026/webex-mcp-lab/mcp_servers"
```


Replace the paths, then verify the registration and start Codex from the VS Code
terminal:

```powershell
codex mcp list
codex
```

example

```
PS C:\WebexOne\31.08.2026\WebexOne2026> codex mcp list
Name           Command                                                                                                        Args             Env                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         Cwd                                                Status   Auth       
node_repl      C:\Users\Administrator.DCLOUD\AppData\Local\OpenAI\Codex\runtimes\cua_node\950613ca46815e82\bin\node_repl.exe  -                BROWSER_USE_AVAILABLE_BACKENDS=*****, BROWSER_USE_CODEX_APP_BUILD_FLAVOR=*****, BROWSER_USE_CODEX_APP_VERSION=*****, BROWSER_USE_TINYSKY_ENABLED=*****, CODEX_CLI_PATH=*****, CODEX_HOME=*****, NODE_REPL_INSTRUCTIONS_USE_CASE_BROWSER=*****, NODE_REPL_INSTRUCTIONS_USE_CASE_CHROME=*****, NODE_REPL_NATIVE_PIPE_CONNECT_TIMEOUT_MS=*****, NODE_REPL_NODE_MODULE_DIRS=*****, NODE_REPL_NODE_PATH=*****, NODE_REPL_TRUSTED_CODE_PATHS=*****, NODE_REPL_TRUSTED_SERVICES=*****, SKY_CUA_NATIVE_PIPE=*****, SKY_CUA_NATIVE_PIPE_DIRECTORY=*****  -                                                  enabled  Unsupported
webex-mcp-lab  C:/WebexOne/31.08.2026/WebexOne2026/webex-mcp-lab/.venv/Scripts/python.exe                                     01_hello_mcp.py  -                                                                                                                   
```


Ask Codex to `use MCP to clean the number (415) 555-0101`. It starts the
server, discovers `format_phone`, and asks for approval before calling it.
For the complete Codex walkthrough and log locations, see
[Using Codex as an MCP client](codex-mcp-client.md).

### The Webex bot client

The alternative host is a small MCP client that runs inside a Webex bot, so the
conversation with your server happens in a Webex space. Configuration is the
same shape — a command, its arguments, and the environment.

![The Webex bot MCP client listing the tools offered by the lab server inside a Webex space]()

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
| 01 logging companion | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/01_hello_mcp_protocol_log.py` |
| 02 | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/02_hello_resource.py` |
| 03 | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/03_hello_prompt.py` |
| 04 | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/04_list_books.py` |
| 05 | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/05_list_entries.py` |
| 06 | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/06_write_books.py` |
| 07 | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/07_full_server.py` |
| 07m | `npx -y @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_servers/07_modular/server.py` |

Chapters 01–03 and the logging companion need no credentials. Chapters 04-07 load
the same `.env` file used by the other clients, so fill in the Webex Contact
Center credentials before connecting. On macOS or Linux, replace
`.venv/Scripts/python.exe` with `.venv/bin/python`.


---

## Chapter 02 — the resource primitive (hello, no network)

**File: `mcp_servers/02_hello_resource.py`**

Still no Webex, still no credentials. This chapter adds MCP's second
primitive on top of the same tool: a **resource**.

```python
@mcp.resource("lab://phone-policy")
def phone_policy() -> str:
    return (
        "Contact Center phone-number policy for this organization:\n"
        "\n"
        "1. Allowed country codes: +1 (US/Canada), +44 (UK), +49 (Germany).\n"
        "   Numbers with any other country code MUST be refused.\n"
        "\n"
        "2. The +1-555-0100 through +1-555-0199 range is reserved for\n"
        "   internal testing. Refuse any number in that range.\n"
        "\n"
        "3. Normalize with format_phone before checking rules 1 and 2."
    )
```

A resource is not a tool. **A tool is an action the *model* decides to
take; a resource is context the *client* attaches to the conversation,
like handing the model a house rulebook before it starts work.** Reading a
resource changes nothing on the server — which is exactly why the client
can pull it in without asking you first.

Notice what's happening here: **the tool doesn't know these rules exist.**
`format_phone` mechanically normalizes any digits you give it, French or
otherwise. The policy lives entirely in the resource, and it only shapes
behaviour because the client attaches it and the model reads it. That's
the whole shape of a resource: **policy the tool cannot enforce alone.**

### Why the resource earns its keep

Try each of these against a client that has attached the resource, and one
that hasn't. The tool call returns the same value in both columns; what
changes is what the model *decides* to do next.

|  | Without `lab://phone-policy` | With `lab://phone-policy` |
|---|---|---|
| `format_phone("+33 1 42 68 53 00")` | Model returns `"+33142685300"` and calls it a win | Model reads the policy, sees +33 is not allowed, **refuses and asks for a supported number** |
| `format_phone("415-555-0142")` | Model returns `"+14155550142"` and hands it back | Model reads the policy, spots the test range, **refuses and flags it as reserved** |
| Editing the resource to also allow +33 | Nothing changes; tool code is unchanged | The model's decisions change on the next `resources/read`, without any code deploy |

The tool implements the mechanics; the resource carries the policy. That
is the pattern to remember.

> **Soft vs. hard enforcement.** Because the policy lives in text the
> model reads, this is *soft* enforcement — a determined or overconfident
> model can still ignore it. That's a real trade-off, not a bug. Chapter
> 06 shows the other end: hard invariants that live in the tool code
> itself, so no amount of coaxing can bypass them. Both patterns have a
> place; you'll typically use resources for policies that change often and
> tool-code for invariants that must never change.

**Ask your client:** *"clean these numbers: (415) 555-0101, +33 1 42 68 53
00, 415-555-0142"*. If the client has attached the resource, you should
see one accepted number and two refusals with reasons.

### Try it from the command line

```
python mcp_clients/02_hello_resource_client.py
python mcp_clients/02_hello_resource_client.py --verbose
```

In verbose mode, two new JSON-RPC methods appear: `resources/list` and
`resources/read`. The client discovers the resource, reads it, then calls
the tool — so you see both primitives exercised in a single session.

---

## Chapter 03 — the prompt primitive (hello, no network)

**File: `mcp_servers/03_hello_prompt.py`**

Still no Webex, still no credentials. This chapter adds the third and final
MCP primitive on top of chapter 02: a **prompt**.

```python
@mcp.prompt()
def clean_contact_list(raw_numbers: str = "") -> str:
    return (
        "Review these phone numbers against our policy:\n\n"
        f"{raw_numbers or '<paste numbers here, one per line - policy will be applied>'}\n\n"
        "1. Read the lab://phone-policy resource for the org rules.\n"
        "2. Call format_phone once for every line to normalize it.\n"
        "3. Reject any number that violates rule 1 (country) or rule 2 (test range).\n"
        "4. Return two lists back to me: accepted (E.164) and rejected (with reason)."
    )
```

A prompt is the one primitive a human triggers directly — usually from a
slash command or a menu. What it returns is not an answer. **It is the
opening message the model sees, as if the user had typed it.** The model
then carries out the workflow using the tools and resources from the same
server.

Notice the argument: `raw_numbers`. Prompt arguments become fields the
client asks the user to fill in before the workflow starts. Paste a list of
numbers, hit go, and the model reads the policy, normalizes each number
with `format_phone`, then hands you back **two** lists — the numbers that
passed the policy and the numbers that were rejected, with the reason next
to each rejection.

### Why the prompt earns its keep

|  | Without `clean_contact_list` | With `clean_contact_list` |
|---|---|---|
| Running the workflow | The user has to type the whole plan every time | The user picks it from a menu and pastes the list |
| Consistency | Each run may skip a step or forget the resource | Every run reads the policy, iterates, and partitions |
| Output shape | Bare list of cleaned numbers | Two lists: **accepted** (E.164) and **rejected** (with reason) |
| Discoverability | The user has to know the tool and resource exist | The prompt appears in the client's slash menu next to the server |

### The three primitives, side by side

All three primitives are now in one file, and the difference between them is
*who reaches for them*:

| Primitive | Who invokes it | What it is | Example in this chapter |
|---|---|---|---|
| tool | the model | an action | `format_phone(number)` |
| resource | the client | policy / reference material | `lab://phone-policy` |
| prompt | the **user** | a starting point | `clean_contact_list(raw_numbers)` |

### Try it from the command line

```
python mcp_clients/03_hello_prompt_client.py
python mcp_clients/03_hello_prompt_client.py --verbose
```

Two more new JSON-RPC methods: `prompts/list` and `prompts/get`. The verbose
output now shows all three MCP primitives exercised in a single session.

---

## Chapter 04 — the first real Webex call: list address books

**File: `mcp_servers/04_list_books.py`**

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
python mcp_clients/04_list_books_client.py
python mcp_clients/04_list_books_client.py --verbose
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

## Chapter 05 — id chaining: list the entries inside a book

**File: `mcp_servers/05_list_entries.py`**

Chapter 04 listed address books. Each book in the result has an `id`. This
chapter uses that id to look inside a book and list its contacts — carrying the
output of one call into the input of the next.

Nothing is written. Both tools here are pure reads. The idea is to practise
chaining before mutation enters the picture in chapter 06.

The server exposes two tools:

- `list_address_books` — the same read-only tool from chapter 04, carried
  forward so this chapter is standalone.
- `list_entries(address_book_id, search="")` — takes the `id` you got from
  listing books and returns the contacts inside that book.

Ask your client: *"list my address books, then show me the entries in the first
one"* — and watch the model carry the id from the first call into the second.

### Try it from the command line

```
python mcp_clients/05_list_entries_client.py
python mcp_clients/05_list_entries_client.py --verbose
```

The client does the chaining for you: it calls `list_address_books`, takes the
first book's id, and passes it to `list_entries`. In verbose mode you see two
`tools/call` frames on the wire, the second carrying the id from the first
response — chaining made visible at the protocol level.

If your organization has no address books yet, the client reports there is
nothing to chain and exits cleanly.

---

## Chapter 06 — writing: create a book, then fill it

**File: `mcp_servers/06_write_books.py`**

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
python mcp_clients/06_write_books_client.py
python mcp_clients/06_write_books_client.py --verbose
```

The client lists all four tools but only calls `list_address_books` — it is
read-only by design, so running it cannot modify your organization. In verbose
mode, notice that `tools/list` now returns four tools instead of one.

---

## Chapter 07 — capstone: prompt + resource + tools on the real API

**File: `mcp_servers/07_full_server.py`**

Every primitive you have learned — tool, resource, prompt — cooperates in one
file, on the real Contact Center API. The capstone registers:

- **One prompt** (`set_up_address_book`) — a workflow that orchestrates
  everything below.
- **One resource** (`webex://address-books/conventions`) — the house style
  guide that shapes how the tools are used.
- **Three tools** — `list_address_books`, `create_address_book`, and
  `add_entry`.

There is no `list_entries` tool here. That is deliberate: you already built it
in chapter 05, and the capstone's prompt does not need it. Keeping it out makes
the file shorter and the story cleaner.

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

> **Why not stderr?** The capstone produces a lot of debug traffic (three tools
> times multiple HTTP calls). Writing it to a file keeps the terminal clean
> while still giving you full observability after the fact.

Ask your client: *"set up an address book called Lab Contacts for the support
team"* — then open `mcp_servers/07_full_server.log` to see everything the
server did.

> **Note:** The older `05_resource.py` and `06_prompt.py` files are the
> pre-restructure demos that taught each primitive with full API calls.
> They are superseded by this capstone; you can delete them after verifying
> chapter 07 runs.

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
is the modular form of chapters 04–07, and it shows the pattern you would follow
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

In chapters 04–07 each tool wrote its own DEBUG lines; here that moves into
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
| `mcp_servers/02_hello_resource.py` | `mcp_clients/02_hello_resource_client.py` | No |
| `mcp_servers/03_hello_prompt.py` | `mcp_clients/03_hello_prompt_client.py` | No |
| `mcp_servers/04_list_books.py` | `mcp_clients/04_list_books_client.py` | Yes |
| `mcp_servers/05_list_entries.py` | `mcp_clients/05_list_entries_client.py` | Yes |
| `mcp_servers/06_write_books.py` | `mcp_clients/06_write_books_client.py` | Yes |
| `mcp_servers/07_full_server.py` | — | Yes |

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
