# Build a Webex MCP server

A hands-on lab. By the end you will have written a server that lets an AI
assistant read your Webex spaces, post messages, and manage Webex Contact
Center address books — and you will understand every line of it.

---

## Before anything else: how this lab works

**Every step is a complete, standalone program.** There are eight of them:

```
01_hello_mcp.py       the smallest server that works
02_whoami.py          the first real Webex call
03_rooms.py           returning a collection
04_send_message.py    the first write
05_resource.py        the second primitive: a resource
06_prompt.py          the third primitive: a prompt
07_address_book.py    a second API family: Contact Center
08_modular/           the same server, built to grow
```

Each file runs on its own. `03_rooms.py` does not import `02_whoami.py`, and
none of them import a shared helper module. That means a step never breaks
because you skipped the one before it.

**Arrived late?** Good news: you have missed nothing you cannot recover in two
minutes. Do the setup chapter below, then open whichever file the room is
currently on and run it. The earlier steps are still there when you want them,
and reading them afterwards costs nothing — each is under 150 lines and stands
completely alone.

The repetition between files is on purpose. Each one is meant to be read from
top to bottom without following an import anywhere else.

---

## Setup

You need three things: Python, `uv`, and a Webex access token. Nothing is
generated, nothing is stored, and there is no sign-in flow to complete.

### 1. Install uv

`uv` runs Python and installs dependencies. Pick your platform:

**Windows (PowerShell)**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS and Linux**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen your terminal, then check it:

```
uv --version
```

### 2. Get the lab files and install dependencies

```
cd webex-mcp-lab
uv sync
```

That installs exactly two packages, `mcp` and `httpx`, into a local `.venv`.

### 3. Get a Webex access token

Go to **https://developer.webex.com/docs/getting-started** and sign in. Your
personal access token is on that page — copy it.

That token is valid for 12 hours and carries your own Webex permissions. If it
expires mid-lab, reload the page and copy the new one.

> If you would rather not use your own account, create a bot at
> **https://developer.webex.com/my-apps** and use its access token instead.
> A bot only sees spaces you have added it to, which for this lab is a feature:
> the blast radius is a space you created for the purpose.

### 4. Put the token in a file

Copy the example file and paste your token in:

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

Set the first line and leave the rest for now:

```
WEBEX_ACCESS_TOKEN=your-token-here
```

`.env` is listed in `.gitignore`. Do not commit it, and do not paste your token
into a chat window or a screenshot.

### 5. Check it works

```
uv run --env-file .env python 01_hello_mcp.py
```

The command will appear to hang. **That is correct.** An MCP server talks over
standard input and output, so there is nothing to print until a client connects.
Press `Ctrl+C` to stop it.

### What you need for which chapter

| Chapters | What you need |
|---|---|
| 01 – 06 | A Webex access token. That is all. |
| 07 | A Webex **Contact Center** organization, plus a token with the `cjp:config_read` and `cjp:config_write` scopes. |
| 08 | A token. Contact Center is optional — chapter 08 explains the one line you remove without it. |

**If you do not have a Contact Center organization, you can complete every
chapter except 07.** You will not be stuck, and chapter 08 is written to work
either way. Decide now which of the two paths you are on so you are not
surprised later.

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
      "command": "uv",
      "args": [
        "run",
        "--directory", "/absolute/path/to/webex-mcp-lab",
        "--env-file", ".env",
        "python", "01_hello_mcp.py"
      ]
    }
  }
}
```

Replace the path with your own, and change the script name as you work through
the chapters. Use forward slashes on every platform, including Windows.

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

Ask your client: *"greet Diego"*.

![The assistant calling the greet tool and returning the greeting](images/01-greet-vscode.png)

---

## Chapter 02 — the first real Webex call

**File: `02_whoami.py`**

Now the tool talks to Webex.

Two things arrive in this step. The first is the token, read once at startup:

```python
TOKEN = os.environ.get("WEBEX_ACCESS_TOKEN")
if not TOKEN:
    sys.exit("WEBEX_ACCESS_TOKEN is not set. Copy .env.example to .env, add "
             "your token, and re-run with --env-file .env")
```

Checking at startup rather than inside the tool is deliberate. A server that
starts fine and then fails on every call is diagnosed by reading HTTP status
codes. A server that refuses to start and names the missing variable is
diagnosed by reading one line.

The second is the shape of the result:

```python
return {
    "display_name": person.get("displayName"),
    "email": (person.get("emails") or [None])[0],
    "type": person.get("type"),
}
```

Webex returns far more than this. We return three fields because **everything a
tool returns is read by a language model** — it becomes context the model has
to process. And the token, obviously, never appears in it.

Ask your client: *"who am I on Webex?"*

![The assistant calling whoami and reporting the signed-in Webex identity](images/02-whoami-vscode.png)

---

## Chapter 03 — returning a collection

**File: `03_rooms.py`**

One tool, one endpoint, one new idea: the API returns a list, and you decide
what the model sees.

```python
rooms = [
    {
        "id": room.get("id"),
        "title": room.get("title"),
        "type": room.get("type"),
        "last_activity": room.get("lastActivity"),
    }
    for room in response.json().get("items", [])
]
```

A raw Webex room record has around twenty fields. We keep four. The `id` is
there because the next chapter needs it to send a message somewhere.

Notice also that `limit` has a default:

```python
async def list_rooms(limit: int = 20) -> dict:
```

A default makes the argument optional in the generated schema, so the model can
call this with no arguments at all. Required arguments are a real cost — every
one is something the model has to work out before it can act.

> If you did last year's bots lab, this endpoint will look familiar. Same call,
> same token. Last year the rooms were printed for a person to read; this year
> they are returned for a model to reason about. That is the whole difference.

Ask your client: *"what Webex spaces am I in?"*

![The assistant listing Webex spaces returned by the list_rooms tool](images/03-rooms-vscode.png)

---

## Chapter 04 — the first write, and who asks permission

**File: `04_send_message.py`**

Everything so far only read. This chapter posts a message.

```python
@mcp.tool()
async def send_message(room_id: str, text: str) -> dict:
```

Now look at what is **not** in that function. There is no `confirm` argument.
There is no dry-run mode. There is no preview step, and the server never stops
to ask you whether you meant it. It posts the message.

That is not an oversight, and it is the most important idea in this lab.

**Consent belongs to the host, not to the server.** Before `send_message` is
entered, your MCP client shows you the tool name and both arguments and waits
for you to approve. Every MCP host does this. It is part of the protocol's
design, not a feature of any particular server.

![The Visual Studio Code approval prompt showing the send_message tool with its room_id and text arguments, waiting for the user to allow or deny](images/04-approval-vscode.png)

So a server that builds its own approval step is not adding safety. It is
adding a second dialog in front of the first one, and teaching its users that
clicking through dialogs is normal. The host already asked. Trust it, and keep
your tool honest about what it does.

What a server *should* do about dangerous operations is a different question,
and the answer is usually "not offer them." You will see that in chapter 07.

Ask your client: *"post 'hello from my MCP server' to the Lab space"* — and
watch for the approval prompt before anything is sent.

![The message delivered in a Webex space, posted by the assistant through the send_message tool](images/04-delivered-webexbot.png)

---

## Chapter 05 — the second primitive: a resource

**File: `05_resource.py`**

MCP has three primitives. You have been using one of them.

```python
@mcp.resource("webex://guidelines/posting")
def posting_guidelines() -> str:
    """House style for messages posted by an assistant."""
```

A **tool** is an action the *model* decides to take. A **resource** is
reference material the *client* attaches to the conversation, the way you would
attach a file. Reading a resource changes nothing — that is exactly why a
client can pull one in without asking you first.

The resource here is a house style for messages, and it exists to shape how
`send_message` gets used. That is the useful pattern: a resource is context
that makes your tools behave better.

The URI is how a client refers to it. The scheme is yours to choose — `webex://`
here — and it need not correspond to anything on a network.

![The resource picker in Visual Studio Code showing the posting guidelines resource offered by the server](images/05-resource-vscode.png)

---

## Chapter 06 — the third primitive: a prompt

**File: `06_prompt.py`**

```python
@mcp.prompt()
def post_status_update(space: str = "", topic: str = "") -> str:
```

Now all three are in one file, and the difference between them is *who reaches
for them*:

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
    f"Post a status update about {topic} to the {space} space.\n"
    "\n"
    "1. Read the webex://guidelines/posting resource and follow it.\n"
    "2. Call list_rooms to find the space and get its id.\n"
    "3. Show me the draft and the space you picked before sending.\n"
    "4. Once I approve, call send_message."
)
```

Read that again as what it is: a workflow, written by the person who knows how
the job should be done, packaged so a user can trigger it without knowing any
of it. The arguments become fields the client asks the user to fill in.

![The prompt appearing as a slash command in the client, with fields for space and topic](images/06-prompt-vscode.png)

---

## Chapter 07 — a second API family: Webex Contact Center

**File: `07_address_book.py`**

> **This chapter needs a Webex Contact Center organization** and a token with
> the `cjp:config_read` and `cjp:config_write` scopes, plus `WEBEX_ORG_ID` and
> `WEBEX_CC_API_BASE` in your `.env`. If you do not have one, skip to
> chapter 08 — nothing there depends on this.

Here is the point of this chapter: **nothing about MCP changes.** The
decorators are the same, the result shapes are the same, the consent model is
the same. Only the URLs and the host differ. Once you can wrap one API, you can
wrap any API — which is the actual reason to learn this.

What does change is the amount of care the domain deserves.

**There are no delete tools in this file.** Not because deleting is hard — it is
the same decorated function as everything else — but because address books are
shared configuration on a shared organization, and the only thing standing in
front of a destructive call is an approval dialog that people click through. A
mistaken create leaves a stray address book for an administrator to remove. A
mistaken delete removes a book and every contact in it. Those are not
comparable, so the verb is simply absent.

Deciding which operations a tool exposes *at all* is a design decision, and it
is a more effective control than any confirmation flow.

The other thing worth copying is the failure handling:

```python
if response.status_code == 403:
    return {"error": "The token lacks Contact Center config permission (cjp:config_write)."}
```

The tool returns a sentence, not an exception. The model can relay it to you,
and the server stays up for the next call.

Ask your client: *"create an address book called Lab Contacts, then add Acme
Reception on +14155550101"*.

![The assistant creating an address book and adding a contact through the Contact Center tools](images/07-address-book-vscode.png)

---

## Chapter 08 — the same server, built to grow

**Directory: `08_modular/`**

Every chapter so far put everything in one file. That is the right shape for
reading and the wrong shape for a server you keep. This chapter is the same
functionality in the shape you would actually maintain.

```
08_modular/
    server.py           decides which domains are switched on
    webex_client.py     credentials and HTTP, resolved once
    tools/
        __init__.py     the contract, written down
        messaging.py    spaces and messages
        address_books.py Contact Center configuration
```

Three kinds of file, and no more.

### The whole extension mechanism

```python
DOMAINS = [
    messaging,
    address_books,
]
```

That is it. **To add a subject area:** write `tools/your_domain.py` with a
`register(mcp, client)` function and add it to that list. **To switch one off:**
delete its line.

> **No Contact Center organization?** Remove `address_books` from `DOMAINS`.
> The server starts and everything else works exactly as before.

Registration is an explicit list rather than a directory scan, so you can read
those four lines and know precisely what the server exposes. So can a reviewer.

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

Here is a complete domain module — this is the whole file:

```python
"""Weather domain."""


def register(mcp, client) -> None:
    @mcp.tool()
    async def forecast(city: str) -> dict:
        """Return the forecast for a city."""
        return {"city": city, "outlook": "sunny"}
```

Add `weather` to `DOMAINS`, restart, and its tool appears alongside the others.
No existing file changes.

### Why credentials live in one place

`webex_client.py` is the only file that reads environment variables and the
only file that holds the token. Domain modules get a `WebexClient` and never
see the credential:

```python
self._token = env.get("WEBEX_ACCESS_TOKEN")
```

That single underscore is doing real work. Because no domain module can reach
the token, no tool schema, tool result, or log line in this server can leak it —
and that is a property you can check by reading one file rather than auditing
every domain.

The client reads every `WEBEX_`-prefixed variable and knows what none of them
are for. Domains that need more than the base token say so at registration
time, in their own words:

```python
settings = client.require(
    "WEBEX_ORG_ID", "WEBEX_CC_API_BASE", needed_by="the address book domain"
)
```

which means a misconfiguration is reported once, at startup, naming both the
missing variable and the domain that wanted it — rather than once per tool
call, as a 403.

![The modular server connected, showing tools from both domains in one list](images/08-modular-vscode.png)

---

## Where to go next

You now have a server you can extend. The obvious next moves:

- **Add a domain.** Meetings, teams, memberships, webhooks — the Webex API is
  large and the contract is four lines.
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
- `<slug>` — what the image shows, in words (`approval`, `rooms`, `modular`)
- `<client>` — the host it was captured in: `vscode` or `webexbot`

Every image needs alternative text describing what is on screen, not just
naming it. `![The Visual Studio Code approval prompt showing the send_message
tool with its arguments](...)` — not `![screenshot](...)`.

Before committing an image, check that no access token, client secret, or
organization identifier is legible anywhere in the frame, including window
titles, terminal scrollback, and browser tabs.
