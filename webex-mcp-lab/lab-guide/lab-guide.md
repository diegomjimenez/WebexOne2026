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

**Every step is a complete, standalone program.** There are six of them:

```
01_hello_mcp.py       the smallest server that works (no network, no token)
02_list_books.py      the first real Contact Center call: list address books
03_write_books.py     writing: create a book, then add contacts to it
04_resource.py        the second primitive: a resource
05_prompt.py          the third primitive: a prompt
06_modular/           the same server, built to grow
```

Each file runs on its own. `04_resource.py` does not import `02_list_books.py`,
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
> but 02–06 will refuse to start and tell you which credential is missing. Decide
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
python 01_hello_mcp.py
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
| 02 – 06 | A Webex **Contact Center** organization, a token with the `cjp:config_read` and `cjp:config_write` scopes, plus `WEBEX_ORG_ID` and `WXCC_CONFIG_API_BASE` in your `.env`. |

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
      "args": ["01_hello_mcp.py"],
      "cwd": "/absolute/path/to/webex-mcp-lab"
    }
  }
}
```

Point `command` at the Python interpreter inside your `.venv`, and set `cwd` to
the lab folder so the server finds your `.env`. On macOS and Linux the
interpreter is `.venv/bin/python` instead of `.venv/Scripts/python.exe`.

Replace both paths with your own, and change the script name as you work through
the chapters (for the modular finale, point `args` at `06_modular/server.py`).
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

**File: `01_hello_mcp.py`**

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

Chapter 01 already uses the same dual-sink logging as the rest of the lab — it
writes to stderr *and* `01_hello_mcp.log`, in the same format, so you can
review the greet calls after the fact. The full explanation is in chapter 02.

Ask your client: *"greet Diego"*.

![The assistant calling the greet tool and returning the greeting](images/01-greet-vscode.png)

---

## Chapter 02 — the first real Webex call: list address books

**File: `02_list_books.py`**

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
    for book in response.json().get("items", [])
]
return {"count": len(books), "address_books": books}
```

Webex wraps collections in an `items` key and each record has many fields. We
unwrap it and keep three, because **everything a tool returns is read by a
language model** — it becomes context the model has to process. The `id` is
there because the next chapter needs it. And the token, obviously, never appears
in the result.

Ask your client: *"list my Contact Center address books"*.

![The assistant listing address books returned by the list_address_books tool](images/02-list-books-vscode.png)

### Watching the server work

Run `02_list_books.py` and call the tool, and you will see more than the banner:

```
2026-08-28 18:20:01,442 DEBUG webex: list_address_books: GET https://api.wxcc-us1.cisco.com/organization/<org>/v3/address-book
2026-08-28 18:20:01,905 DEBUG webex: list_address_books: Webex responded HTTP 200
```

That is the server's own log, and every chapter from here keeps one. It goes to
**two places at once**: the live stderr stream *and* a file next to the script
(`02_list_books.log`, `03_write_books.log`, and so on). A block near the top of
each file sets both up:

```python
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
log = logging.getLogger("webex")
log.setLevel(logging.DEBUG)
log.propagate = False
for _handler in (
    logging.StreamHandler(sys.stderr),
    logging.FileHandler(Path(__file__).with_suffix(".log"), encoding="utf-8"),
):
    _handler.setFormatter(logging.Formatter(LOG_FORMAT))
    log.addHandler(_handler)
```

Five properties are worth naming, because they are why this is safe and useful:

- **It goes to stderr, never stdout.** stdout carries the MCP protocol — a stray
  `print` there corrupts it. Logs belong on stderr, which is exactly where an
  MCP host collects them.
- **It is also written to a file, beside the server.** The path comes from
  `__file__`, so the log lands next to the script no matter which directory the
  host launched it from. The modular server (chapter 06) writes one
  `webex-mcp-lab.log`; each numbered chapter writes its own `NN_<name>.log`.
- **The file appends across runs**, so you can compare today's run against
  yesterday's. `*.log` is git-ignored, so these never get committed.
- **It does not depend on the client.** The level is `DEBUG` in the code, so you
  see the same trace whether the server is driven by VS Code, the bot, or the
  `_check.py` script. Nothing needs to ask for logging.
- **It never logs a secret.** The token is not logged, and neither is a contact's
  phone number (chapter 03). A log line is a decision about what is safe to write
  down — make it deliberately.

Every chapter uses the same block, including chapter 01 — so even the no-network
intro produces `01_hello_mcp.log`, and you can review past greet calls there.

As you work through the chapters the log grows with the feature: a request and
its status in 02–03, the resource read in 04, the prompt firing in 05, and every
Contact Center failure through one line. Chapter 06 collapses all of it into a
single request line written once, in the shared client.

---

## Chapter 03 — writing: create a book, then fill it

**File: `03_write_books.py`**

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

---

## Chapter 04 — the second primitive: a resource

**File: `04_resource.py`**

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

---

## Chapter 05 — the third primitive: a prompt

**File: `05_prompt.py`**

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

---

## Chapter 06 — the same server, built to grow

**Directory: `06_modular/`**

Every chapter so far put everything in one file. That is the right shape for
reading and the wrong shape for a server you keep. This chapter is the same
functionality in the shape you would actually maintain.

```
06_modular/
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
is the modular form of chapters 02–05, and it shows the pattern you would follow
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

In chapters 02–05 each tool wrote its own DEBUG lines; here that moves into
`webex_client.request`, which every domain already calls:

```python
log.debug("-> %s %s", method, url)
...
log.debug("<- HTTP %s (%s %s)", response.status_code, method, url)
```

Write it once and every domain is traced — including one you add tomorrow from
the template, which needs no logging code of its own. The logger is configured
once in `webex_client.py` and shared by name (`logging.getLogger("webex")`), so
`server.py` and each domain reach the same two sinks — stderr and one
`webex-mcp-lab.log` beside the server — with no setup. And because the token
lives only in `WebexClient`, the request log physically cannot contain it.

![The modular server connected, showing the address book tools, resource, and prompt in one list](images/06-modular-vscode.png)

---

## Add your own Webex API family

Chapter 06 gave you the mechanism. Here is the recipe. There is a starting point
in the tree for exactly this: `06_modular/tools/_template.py`. It is a complete
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
