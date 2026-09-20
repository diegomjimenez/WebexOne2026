# Lab 3 - Build a Custom MCP Server

In this chapter you will build an MCP server that lets an AI assistant manage Webex Contact Center address books.

## Step 3.1: Building an MCP Server

Before we write our first line of code, let's talk about how an MCP client (like VS Code) actually talks to an MCP server. The Model Context Protocol supports two primary transport methods: **stdio** and **SSE (Server-Sent Events) over HTTP**.

### Choosing the Right Transport: stdio vs SSE

| Feature | `stdio` (Standard Input/Output) | `SSE` (Streamable HTTP) |
| --- | --- | --- |
| **What is it?** | The client spawns the server as a local background process and communicates by reading/writing to its standard input and output streams. | The server runs as a standalone web service. The client connects over the network using HTTP and Server-Sent Events. |
| **When to use it?** | - Local development and testing.<br>- Tools that run on the same machine as the client (e.g., VS Code connecting to a local script). | - Production deployments.<br>- When the server needs to be shared across multiple clients or users.<br>- When the server is hosted remotely. |
| **Why?** | **Simplicity:** No network configuration, no exposed ports, and the lifecycle is tied to the client (if the client dies, the server dies). | **Scalability:** You can host the server once in the cloud, update it centrally, and have thousands of bots connect to it via URLs. |

In previous labs, your **VS Code** was connected to the official Webex MCP servers using **SSE** (`https://mcp.webexapis.com/...`). 

For this lab, we will build our custom MCP servers using **stdio**. This is the standard approach for local development and allows us to test our tools instantly using the MCP Inspector and VS Code.

### Step 3.1.1: Simple MCP Server

In this section, we are going to start with the simplest MCP server that does real work: one tool, no network, no token. It takes a messy phone number and returns it in E.164 format.

We will use the official `mcp` Python SDK to create our server. The SDK makes it incredibly easy to define tools and their execution logic using decorators.

1. Navigate to `03_custom_mcp/01_hello_mcp.py` and review the code.

    ??? Tip "Python Code"
        ```python
        # Step 01 - the smallest MCP server: one tool, no network, no token.
        
        import logging
        import re
        from mcp.server import MCPServer
        
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        log = logging.getLogger("hello-mcp")
        
        # Create an MCP server instance.
        mcp = MCPServer("hello-mcp")
        
        # Register a tool that cleans a phone number to E.164 format.
        @mcp.tool()
        async def format_phone(number: str) -> str:
            """Clean a phone number to E.164 form, e.g. +14155550101."""
            digits = re.sub(r"\D", "", number)
            if not number.startswith("+") and len(digits) == 10:
                digits = "1" + digits
            return "+" + digits
        
        # Start the server on stdio and wait for a client to connect.
        if __name__ == "__main__":
            log.info("hello-mcp running on stdio - waiting for a client (Ctrl+C to stop).")
            try:
                mcp.run()
            except KeyboardInterrupt:
                log.info("Stopped.")
        ```

    Everything a `@mcp.tool()` decorator does is on display here:
    
    1. **Discovery.** The client learns there is a tool called `format_phone`.
    2. **Description.** The docstring becomes the tool's description. This is not documentation for you — it is how the model decides whether this is the right tool to call. A vague or misleading docstring produces a tool the model misuses.
    3. **Schema.** The `number: str` annotation becomes the input schema, so the client knows to send one string argument.

2. In VS Code, make sure your terminal is in the correct folder:

    * cd ../03_custom_mcp

3. To test our MCP server, we will be using a tool called **MCP Inspector**. It is the official, interactive debugging tool for MCP servers. It runs a local web interface where you can list tools, resources, and prompts, and execute them directly without needing an LLM in the loop.
    
    * npx @modelcontextprotocol/inspector python 01_hello_mcp.py
   
    !!! Note
        If it asks to install the `@modelcontextprotocol/inspector` package, press `y`:

        ```terminal
        Need to install the following packages:
        @modelcontextprotocol/inspector@1.0.2
        Ok to proceed? (y) 
        ```

4. Once it starts, it should open a new tab for you, if not, it will provide a local URL (usually `http://localhost:6274`). Open that URL in your browser.

    ![MCP Inspector Start](assets/inspector_start.png){ style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

5. Select the following and click `Connect`:

    |        	|           |
    |-----------------------	|--------------|
    | **Transport Type**       	| STDIO |
    | **Command**       	| Python |
    | **Arguments**       	| 01_hello_mcp.py |

    ![MCP Inspector Start](assets/inspector_2.png){ width="350" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

6. In the MCP Inspector web interface, click on the **Tools** tab, then **List Tools** and you will see the `format_phone` tool listed.

    ![MCP Inspector Start](assets/inspector_3.png){ style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

7. Click on **format_phone**. In the arguments JSON editor, provide a messy phone number:
    ```json
    {
      "number": "(415) 555-0101"
    }
    ```

8. Click **Run Tool**. You should see the result `+14155550101` returned immediately.

    !!! Note
        You may need to scroll down

    ![MCP Inspector Tool Run](assets/inspector_run.png){ width="600" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

    This confirms your server works perfectly in isolation! You can stop the MCP in your terminal with `Ctrl+C`, we will still use the MCP inspector in the next exercise.

### Step 3.1.2: Tools, Resources and Prompts

Next, we are going to build a single script that demonstrates the entire MCP architecture, which consists of three distinct primitives:

- **A tool** is an action the model calls. 
- **A resource** is context the client attaches, like handing the model a rulebook. 
- **A prompt** is the one primitive a human triggers directly — from a slash command or menu.
</br>
1. Navigate to `03_custom_mcp/02_hello_resource_prompt.py` and review the code:

    ??? Tip "Python Code"
        ```python
        # Step 02 - all three MCP primitives (tool, resource, prompt) without credentials.
        
        import logging
        from mcp.server import MCPServer
        
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        log = logging.getLogger("hello-resource-prompt")
        
        # Create an MCP server instance.
        mcp = MCPServer("hello-resource-prompt")
        
        
        # Register a tool that counts words and characters in a piece of text.
        @mcp.tool()
        async def count_words(text: str) -> dict:
            """Count the words and characters in a piece of text."""
            words = text.split()
            return {"words": len(words), "characters": len(text)}
        
        
        # Register a resource with greeting rules the tool cannot know on its own.
        @mcp.resource("lab://greeting-rules")
        def greeting_rules() -> str:
            return (
                "Webex Contact Center greeting rules for this organization:\n"
                "1. 12 words maximum.\n"
                "2. Must include the agent's first name.\n"
                "3. Never use 'ASAP' or 'obviously'.\n"
            )
        
        
        # Register a prompt that chains the resource and the tool into a review workflow.
        @mcp.prompt()
        def review_greeting(greeting: str = "") -> str:
            """Review an agent greeting against the organization rules."""
            return (
                f"Review this agent greeting:\n\n"
                f"{greeting or '<paste a greeting here>'}\n\n"
                "1. Read the lab://greeting-rules resource for the org rules.\n"
                "2. Call count_words to measure the greeting.\n"
                "3. Tell me pass or fail, and why."
            )
        
        
        # Start the server on stdio and wait for a client to connect.
        if __name__ == "__main__":
            log.info("hello-resource-prompt running on stdio - waiting for a client (Ctrl+C to stop).")
            try:
                mcp.run()
            except KeyboardInterrupt:
                log.info("Stopped.")
        ```

2. Go to the MCP Inspector. Click on **Disconnect**.
3. Change **Arguments** to `02_hello_resource_prompt.py` and click **Connect**.
4. Click on **Resources** and then **List Resources**. You will see `lab://greeting-rules`. You can click it to read the greeting rules.
    ??? Note "Resources"
        ![MCP Inspector Tool Run](assets/resources.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
5. Click on **Prompts** and then **List Prompts**. You will see `review_greeting`.
    ??? Note "Prompts"
        ![MCP Inspector Tool Run](assets/prompts.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
6. Click on **Tools** and then **List Tools**. You will see `count_words`. You can test it by providing a `"text"` argument.
    ??? Note "Tools"
        ![MCP Inspector Tool Run](assets/tools.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

### Step 3.1.3: Reading from Webex Contact Center API

####  Understand Webex Contact Center Address Book APIs

Before connecting to the real API, let's understand how Address Books work in Webex Contact Center. An address book is a named list of contacts that agents see in their desktop. 

Below is a screenshot showing how address books are seen in the agent desktop:

![Agent Desktop](assets/lab6_img29.png){ width="800" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

#### Where are they configured?

They can only be configured by Administrators. In **Collaboration Control Hub** -> **Contact Center**, under **Desktop Experience** section, you have **Address Book**.

![Control Hub](assets/addressbooks_1.png){ width="900" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

One address book is assigned to an agent profile.

#### List Address Books MCP

You can explore Webex Contact Center APIs in the [Webex Developer Portal - WxCC APIs](https://developer.webex.com/webex-contact-center/docs/webex-contact-center).
We will be using the [List Address Book(s) API](https://developer.webex.com/webex-contact-center/docs/api/v1/address-book/list-address-books) 

![Control Hub](assets/addressbooks_2.png){ style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

You can test directly in the UI, using the **Service App** token:

![Control Hub](assets/addressbooks_3.png){ width="700" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

Response should look like:

??? Note "Response"
    ```json
    {
        "meta": {
            "orgid": "74983fd5-5c18-45cb-bfcd-507005e05b0f",
            "page": 0,
            "pageSize": 100,
            "totalPages": 1,
            "totalRecords": 4,
            "links": {
                "self": "/organization/74983fd5-5c18-45cb-bfcd-507005e05b0f/v3/address-book?page=0&pageSize=100"
            }
        },
        "data": [
            {
                "id": "3eaea255-f4d8-4b75-94e3-fe67ef23fb42",
                "name": "HR Team",
                "description": "Human Resources team contacts",
                "parentType": "ORGANIZATION",
                "links": [
                    {
                        "rel": "self",
                        "href": "/organization/74983fd5-5c18-45cb-bfcd-507005e05b0f/v3/address-book/3eaea255-f4d8-4b75-94e3-fe67ef23fb42"
                    }
                ],
                "createdTime": 1789726765000,
                "lastUpdatedTime": 1789726765000
            },
            {
                "id": "568f627a-802e-4c99-a74a-1b59207449c7",
                "name": "Global Directory",
                "description": "",
                "parentType": "SITE",
                "siteId": "b0e6657f-aefe-4309-a32e-30abe14a3d98",
                "links": [
                    {
                        "rel": "self",
                        "href": "/organization/74983fd5-5c18-45cb-bfcd-507005e05b0f/v3/address-book/568f627a-802e-4c99-a74a-1b59207449c7"
                    },
                    {
                        "rel": "site",
                        "href": "/organization/74983fd5-5c18-45cb-bfcd-507005e05b0f/site/b0e6657f-aefe-4309-a32e-30abe14a3d98"
                    }
                ],
                "createdTime": 1789726749000,
                "lastUpdatedTime": 1789726749000
            },
            {
                "id": "b7d7a924-1615-494e-9d1e-81623b991fbf",
                "name": "Technical Support Partners",
                "description": "",
                "parentType": "ORGANIZATION",
                "links": [
                    {
                        "rel": "self",
                        "href": "/organization/74983fd5-5c18-45cb-bfcd-507005e05b0f/v3/address-book/b7d7a924-1615-494e-9d1e-81623b991fbf"
                    }
                ],
                "createdTime": 1789726854000,
                "lastUpdatedTime": 1789726854000
            },
            {
                "id": "be30e08a-0ae1-4f83-8438-dfbf630155eb",
                "name": "Internal Directory",
                "description": "Organization-wide internal contact directory",
                "parentType": "ORGANIZATION",
                "links": [
                    {
                        "rel": "self",
                        "href": "/organization/74983fd5-5c18-45cb-bfcd-507005e05b0f/v3/address-book/be30e08a-0ae1-4f83-8438-dfbf630155eb"
                    }
                ],
                "createdTime": 1789726828000,
                "lastUpdatedTime": 1789726828000
            }
        ]
    }
    ```

We are going to build now an MCP server that talks to the Webex Contact Center APIs and exposes two read-only tools — `list_address_books` and `list_entries`.

We will need the following three values `ACCESS_TOKEN`, `WEBEX_ORG_ID` and `WXCC_CONFIG_API_BASE`.

??? Tip "ACCESS_TOKEN, WEBEX_ORG_ID & WXCC_CONFIG_API_BASE"
    - **`ACCESS_TOKEN`**: This is going to be the Service App token created in the previous task.
    - **`WEBEX_ORG_ID`** and **`WXCC_CONFIG_API_BASE`**: These are related to the sandbox and will be set up in advance for you, but here is how you could find them:
    
        For `WEBEX_ORG_ID`, you need to go in Collaboration Control Hub to Account:
    
        ![Org ID](assets/orgid_1.png){ width="850" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
    
        For `WXCC_CONFIG_API_BASE`, you can find it using this information (in this case it will be `us1`):
    
        ![API Base](assets/orgid_2.png){ width="850" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
    
        While general Webex APIs use a global endpoint (`https://webexapis.com/v1`), Webex Contact Center (WxCC) specific data and agent APIs route through regional endpoints. [1](https://www.cisco.com/c/en/us/support/docs/contact-center/webex-contact-center/218418-configure-webex-contact-center-apis-with.html)
        
        The region can be identified through the following methods:
        
        1. **Check in Webex Control Hub**
           You can find your data residency/region directly inside the dashboard: [1](https://community.cisco.com/t5/webex-for-developers/programmatically-retrieve-the-data-center-instance-for-contact/m-p/5252255)
           - Log into Webex Control Hub.
           - Navigate to Services > Contact Center > Tenant Settings.
           - Go to General > Service Details.
           - Look for the Country of Operation or data center zone field. [1](https://cloud.cloverhound.com/docs/campaigns/integration), [2](https://community.cisco.com/t5/webex-for-developers/programmatically-retrieve-the-data-center-instance-for-contact/m-p/5252255)
           
        2. **Map Region to the Correct API Base URL**
           Once you know the country or code of operation, match it to the standard Webex Contact Center datacenter variables (`us1`, `eu1`, `eu2`, `anz1`, `jp1`, `sg1`): [1](https://help.webex.com/en-us/article/n1lsqvu/Integrate-Webex-Contact-Center-CRM-Connector-for-Microsoft-Dynamics-365-(Version2-New)), [2](https://www.cisco.com/c/en/us/support/docs/contact-center/webex-contact-center/218418-configure-webex-contact-center-apis-with.html)
           
           | Region / Operation Location | Datacenter Variable | API Base URL Example |
           | --- | --- | --- |
           | North America | `us1` | `https://api.wxcc-us1.cisco.com` |
           | United Kingdom | `eu1` | `https://api.wxcc-eu1.cisco.com` |
           | Europe | `eu2` | `https://api.wxcc-eu2.cisco.com` |
           | APJC (Australia / NZ) | `anz1` | `https://api.wxcc-anz1.cisco.com` |
           | Japan | `jp1` | `https://api.wxcc-jp1.cisco.com` |
           | Singapore | `sg1` | `https://api.wxcc-sg1.cisco.com` |

        If you have logged in to the Webex for Developers portal with an account from that organization, you should also be able to find this information in the Code Snippets examples:
        ![Org ID](assets/api_1.png){ width="750" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

1. Navigate to `03_custom_mcp/03_read_books.py` and review the code:

    ??? Tip "Python Code"
        ```python
        # Step 03 - reading: list address books, then list entries inside one book.
        
        import logging
        import os
        import sys
        import httpx
        from dotenv import load_dotenv
        from mcp.server import MCPServer
        
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        log = logging.getLogger("read-books")
        
        # Load credentials from .env.
        load_dotenv()
        
        TOKEN = os.environ.get("ACCESS_TOKEN")
        ORG_ID = os.environ.get("WEBEX_ORG_ID")
        CONFIG_API_BASE = os.environ.get("WXCC_CONFIG_API_BASE", "")
        
        # Stop early if any credential is missing.
        for _name, _value in (
            ("ACCESS_TOKEN", TOKEN),
            ("WEBEX_ORG_ID", ORG_ID),
            ("WXCC_CONFIG_API_BASE", CONFIG_API_BASE),
        ):
            if not _value:
                sys.exit(f"{_name} is not set. This lab needs Webex Contact Center - see .env.example.")
        
        # Build the API base URL and common headers.
        ORG = f"{CONFIG_API_BASE.rstrip('/')}/organization/{ORG_ID}"
        HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
        
        # Create an MCP server instance.
        mcp = MCPServer("read-books")
        
        
        # List all address books in the Contact Center organization.
        @mcp.tool()
        async def list_address_books(limit: int = 50) -> dict:
            """List the address books configured in this Contact Center organization."""
            async with httpx.AsyncClient(timeout=15) as http:
                response = await http.get(
                    f"{ORG}/v3/address-book", headers=HEADERS, params={"pageSize": limit}
                )
        
            if response.status_code != 200:
                return {"error": f"Webex Contact Center returned HTTP {response.status_code}."}
        
            books = [
                {"id": book.get("id"), "name": book.get("name"), "description": book.get("description")}
                for book in response.json().get("data", [])
            ]
            return {"count": len(books), "address_books": books}
        
        
        # List contacts inside one address book, using its id from list_address_books.
        @mcp.tool()
        async def list_entries(address_book_id: str, search: str = "") -> dict:
            """List the contacts inside one address book, optionally filtered by `search`.
        
            Pass the `address_book_id` returned by list_address_books.
            """
            params: dict = {"page": 0, "pageSize": 100}
            if search:
                params["search"] = search
        
            async with httpx.AsyncClient(timeout=15) as http:
                response = await http.get(
                    f"{ORG}/v2/address-book/{address_book_id}/entry", headers=HEADERS, params=params
                )
        
            if response.status_code != 200:
                return {"error": f"Webex Contact Center returned HTTP {response.status_code}."}
        
            entries = [
                {"id": entry.get("id"), "name": entry.get("name"), "number": entry.get("number")}
                for entry in response.json().get("data", [])
            ]
            return {"count": len(entries), "entries": entries}
        
        
        # Start the server on stdio and wait for a client to connect.
        if __name__ == "__main__":
            log.info("read-books running on stdio - waiting for a client (Ctrl+C to stop).")
            try:
                mcp.run()
            except KeyboardInterrupt:
                log.info("Stopped.")
        ```

2. Go to the MCP Inspector. Click on **Disconnect**.
3. Change **Arguments** to `03_read_books.py` and click **Connect**.
4. Click on **Tools** and then **List Tools**. You will see both `list_address_books` and `list_entries`. Now, we will test them.

    !!! Warning
        For these API calls to work, you need to have `cjp:config_read` scope added to your Service App. If you didn't do it before, you need to add it, re-authorize your Service App and generate a new access token!

5. Run the `list_address_books` tool:

    ![List Address Books](assets/tools_4.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
    ??? Note "Result"
        ```json
        {
          "count": 4,
          "address_books": [
            {
              "id": "3eaea255-f4d8-4b75-94e3-fe67ef23fb42",
              "name": "HR Team",
              "description": "Human Resources team contacts"
            },
            {
              "id": "568f627a-802e-4c99-a74a-1b59207449c7",
              "name": "Global Directory",
              "description": ""
            },
            {
              "id": "b7d7a924-1615-494e-9d1e-81623b991fbf",
              "name": "Technical Support Partners",
              "description": ""
            },
            {
              "id": "be30e08a-0ae1-4f83-8438-dfbf630155eb",
              "name": "Internal Directory",
              "description": "Organization-wide internal contact directory"
            }
          ]
        }
        ```
6. Run the `list_entries` tool:

    ![List Entries](assets/tools_5.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
    ??? Note "Result"
        ```json
        {
          "count": 1,
          "entries": [
            {
              "id": "379233b6-be13-4b3e-850f-ac945eb5a660",
              "name": "John M",
              "number": "+48573244479"
            }
          ]
        }
        ```

### Step 3.1.4: Create and Fill an Address Book

Now, we are going to include the tools that perform writing actions. We are going to build two tools, `create_address_book` and `add_entry`. 

1. Navigate to `03_custom_mcp/04_write_books.py` and review the code:

    ??? Tip "Python Code"
        ```python
        # Step 04 - writing: create an address book, then fill it with contacts.
        
        import logging
        import os
        import sys
        import httpx
        from dotenv import load_dotenv
        from mcp.server import MCPServer
        
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        log = logging.getLogger("write-books")
        
        # Load credentials from .env.
        load_dotenv()
        
        TOKEN = os.environ.get("ACCESS_TOKEN")
        ORG_ID = os.environ.get("WEBEX_ORG_ID")
        CONFIG_API_BASE = os.environ.get("WXCC_CONFIG_API_BASE", "")
        
        # Stop early if any credential is missing.
        for _name, _value in (
            ("ACCESS_TOKEN", TOKEN),
            ("WEBEX_ORG_ID", ORG_ID),
            ("WXCC_CONFIG_API_BASE", CONFIG_API_BASE),
        ):
            if not _value:
                sys.exit(f"{_name} is not set. This lab needs Webex Contact Center - see .env.example.")
        
        # Build the API base URL and common headers.
        ORG = f"{CONFIG_API_BASE.rstrip('/')}/organization/{ORG_ID}"
        HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
        
        # Create an MCP server instance.
        mcp = MCPServer("write-books")
        
        
        # Turn an HTTP failure into a sentence the model can relay to the user.
        def _fail(response: httpx.Response) -> dict:
            """Turn an HTTP failure into a sentence the model can pass on to the user."""
            if response.status_code == 401:
                return {"error": "Webex rejected the token. Check that it has not expired."}
            if response.status_code == 403:
                return {"error": "The token lacks Contact Center config permission (cjp:config_write)."}
            if response.status_code == 404:
                return {"error": "No such address book in this organization."}
            if response.status_code == 429:
                return {"error": "Rate limited by Webex. Wait a moment and try again."}
            return {"error": f"Webex Contact Center returned HTTP {response.status_code}."}
        
        
        # Create a new address book and return its id.
        @mcp.tool()
        async def create_address_book(name: str, description: str = "") -> dict:
            """Create a new address book. Returns its id, which add_entry then needs.
        
            The MCP client asks the user for approval before this runs.
            """
            async with httpx.AsyncClient(timeout=15) as http:
                response = await http.post(
                    f"{ORG}/v3/address-book",
                    headers=HEADERS,
                    json={"name": name, "description": description, "parentType": "ORGANIZATION"},)
        
            if response.status_code not in (200, 201):
                return _fail(response)
        
            book = response.json()
            return {"created": True, "address_book_id": book.get("id"), "name": book.get("name")}
        
        
        # Add a contact to an address book using the id from create_address_book.
        @mcp.tool()
        async def add_entry(address_book_id: str, name: str, number: str) -> dict:
            """Add a contact to an address book. `number` should be E.164, e.g. +14155550101.
        
            `address_book_id` is what create_address_book returned. The MCP client asks
            the user for approval before this runs.
            """
            async with httpx.AsyncClient(timeout=15) as http:
                response = await http.post(
                    f"{ORG}/address-book/{address_book_id}/entry",
                    headers=HEADERS,
                    json={"name": name, "number": number},
                )
        
            if response.status_code not in (200, 201):
                return _fail(response)
        
            return {"added": True, "entry_id": response.json().get("id"), "name": name}
        
        
        # Start the server on stdio and wait for a client to connect.
        if __name__ == "__main__":
            log.info("write-books running on stdio - waiting for a client (Ctrl+C to stop).")
            try:
                mcp.run()
            except KeyboardInterrupt:
                log.info("Stopped.")
        ```

2. Go to the MCP Inspector. Click on **Disconnect**.
3. Change **Arguments** to `04_write_books.py` and click **Connect**.
4. Click on **Tools** and then **List Tools**. You will see both `create_address_book` and `add_entry`. You will be testing both now.

   !!! Warning
       For these API calls to work, you need to have `cjp:config_read` and `cjp:config_write` scope added to your Service App. If you didn't do it before, you need to add it, re-authorize your Service App and generate a new access token!

5. Create an Address Book with name "WebexOne - Username":

    ![Create Address Book](assets/tools_6.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
    !!! Note "Result"
        ```json
        {
          "created": true,
          "address_book_id": "ef60d796-ce1a-40c3-ae1d-7b1968c84bdc",
          "name": "WebexOne - Diejimen"
        }
        ```

6. Using the `address_book_id` provided, create an Entry, with your name and number:

    ![Add Entry](assets/tools_7.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
    !!! Note "Result"
        ```json
        {
          "added": true,
          "entry_id": "ce5471b8-7733-4de6-aeb3-bc2420f177e0",
          "name": "Diego"
        }
        ```

7. You could verify it was added using the tools in the previous exercise.

## Step 3.2: Register in your IDE

In this section, you will add and test your custom MCP servers directly in VS Code.

1. Add the following configuration to `mcp.json`. Delete what we added before and save the file afterwards:

    ```json
    {
      "servers": {
        "webex-mcp-lab": {
          "command": "${workspaceFolder}/webexone/bin/python",
          "args": ["03_custom_mcp/01_hello_mcp.py"],
          "cwd": "${workspaceFolder}"
        }
      }
    }
    ```
    
    You can change the `args` array to point to the specific script you want to test (e.g., `01_hello_mcp.py`, `03_read_books.py`, etc.) or add all of them:

    ??? Note "MCP servers"
        ```json
        {
          "servers": {
            "hello-mcp": {
              "command": "${workspaceFolder}/webexone/bin/python",
              "args": ["03_custom_mcp/01_hello_mcp.py"],
              "cwd": "${workspaceFolder}"
            },
            "hello-resource-prompt": {
              "command": "${workspaceFolder}/webexone/bin/python",
              "args": ["03_custom_mcp/02_hello_resource_prompt.py"],
              "cwd": "${workspaceFolder}"
            },
            "read-books": {
              "command": "${workspaceFolder}/webexone/bin/python",
              "args": ["03_custom_mcp/03_read_books.py"],
              "cwd": "${workspaceFolder}"
            },
            "write-books": {
              "command": "${workspaceFolder}/webexone/bin/python",
              "args": ["03_custom_mcp/04_write_books.py"],
              "cwd": "${workspaceFolder}"
            }
          }
        }
        ```

        We use VS Code variables like `${workspaceFolder}` so the configuration works on any machine without hardcoding absolute paths. If you are on Windows, the command would be `${workspaceFolder}/webexone/Scripts/python.exe`.

2. Start the MCP server.

    a. Click the "Start" button in the `mcp.json` file:

        ![Start MCP](assets/lab6_img02.png){ width="850" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

    b. Or use the Command Palette (`Ctrl+Shift+P` -> `MCP: List Servers`).

        ![List Servers](assets/lab6_img05.png){ width="750" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

3. You will see MCP server logs in the Output section automatically:

    ```terminal
    2026-09-18 17:35:44.757 [info] Starting server webex-mcp-lab
    2026-09-18 17:35:44.758 [info] Connection state: Starting
    2026-09-18 17:35:44.758 [info] Starting server from LocalProcess extension host
    2026-09-18 17:35:44.760 [info] Connection state: Starting
    2026-09-18 17:35:44.760 [info] Connection state: Running
    2026-09-18 17:35:45.231 [warning] [server stderr] 2026-09-18 17:35:45,230 INFO hello-mcp running on stdio - waiting for a client (Ctrl+C to stop).
    2026-09-18 17:35:45.240 [info] Discovered 1 tools
    ```
    
4. Open VS Code Chat view and test your tools!

    1. **Testing 01_hello_mcp.py:**

        - Ask: *"Clean the number (415) 555-0101"*. 
    
            ![Chat Format](assets/test1.png){ width="500" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
            ![Chat Format](assets/test2.png){ width="500" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

    2. **Testing 02_hello_resource_prompt.py:**
    
        1. First, we are going to test the resource.
        
            !!! Warning
                For Resources, there are currently two bugs in VS Code:
                
                - [Bug 291004](https://github.com/microsoft/vscode/issues/291004)
                - [Bug 251747](https://github.com/microsoft/vscode/issues/251747)
                
                For now, you will need to add them manually.
                
                - At the bottom of the chat window, click  **+**, then **Add Context** -> **MCP Resources** -> `lab://greeting-rules`
    
                ??? Note "Images"
                    ![Ask Rules](assets/test3.png){ width="650" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
                    ![Ask Rules](assets/test4.png){ width="550" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
                    ![Ask Rules](assets/test5.png){ width="550" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
    
            - Ask: *"What are the greeting rules?"*
            
                ![Ask Rules](assets/test6.png){ width="600" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

        2. To test a prompt, you will load it on demand, start typing "/mcp" in the chat, and you will see the prompt:

            ![Prompt](assets/prompt_1.png){ width="600" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

            - Select "Insert as text":

                ![Prompt](assets/prompt_2.png){ width="600" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
        
            - Complete with the following test: *"Hello! I'm Sam and I'll obviously get back to you ASAP with a full resolution of your issue as soon as humanly possible."*

                ![Prompt](assets/prompt_3.png){ width="500" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
                ![Prompt](assets/prompt_4.png){ width="500" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
                ![Prompt](assets/prompt_5.png){ width="500" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

    4. **Testing 03_read_books.py:**
    
        - Ask: *"List my address books, then show me the entries for WebexOne - Diejimen"*
    
            ![List Books](assets/test7.png){ width="500" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
            ![List Books](assets/test8.png){ width="500" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
            ![List Books](assets/test9.png){ width="500" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

    5. **Testing 04_write_books.py:**
    
        - Ask: *"Create an address book called WebexOne - Diejimen2"*  
        
            ![Create Book](assets/test10.png){ width="500" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
            ![Create Book](assets/test11.png){ width="500" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

        - Ask: *"Add an entry to the book, for number +1415555-0101"*
        
            ![Created Book](assets/test12.png){ width="500" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
            ![Created Book](assets/test13.png){ width="500" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

            As no more information was provided, the agent added the name "Test Contact"

## Extra: Elicitation

So far, we trusted the host (VS Code) to ask permission before executing a tool. But what happens when the server itself needs to ask a question mid-call, like confirming a destructive action? 

The MCP protocol calls this **elicitation**: the server pauses, sends a form to the user, and resumes based on the answer.

Now, we will add to the server two destructive tools: `delete_address_book` and `delete_entry`. 

1. Navigate to `03_custom_mcp/05_delete_books.py` and review the code:

    ??? Tip "Python Code"
        ```python
        # Step 05 - deleting with a safety net: elicitation asks "are you sure?" mid-call.
    
        import os
        import sys
        from typing import Annotated
    
        import httpx
        from dotenv import load_dotenv
        from mcp.server import MCPServer
    
        # Elicitation imports: the resolver pattern lets the server ask the user a question mid-call.
        from mcp.server.mcpserver import (
            AcceptedElicitation,
            CancelledElicitation,
            DeclinedElicitation,
            Elicit,
            ElicitationResult,
            Resolve,
        )
        from pydantic import BaseModel
    
        # Load credentials from .env.
        load_dotenv()
    
        TOKEN = os.environ.get("ACCESS_TOKEN")
        ORG_ID = os.environ.get("WEBEX_ORG_ID")
        CONFIG_API_BASE = os.environ.get("WXCC_CONFIG_API_BASE", "")
    
        # Stop early if any credential is missing.
        for _name, _value in (
            ("ACCESS_TOKEN", TOKEN),
            ("WEBEX_ORG_ID", ORG_ID),
            ("WXCC_CONFIG_API_BASE", CONFIG_API_BASE),
        ):
            if not _value:
                sys.exit(f"{_name} is not set. This lab needs Webex Contact Center - see .env.example.")
    
        # Build the API base URL and common headers.
        ORG = f"{CONFIG_API_BASE.rstrip('/')}/organization/{ORG_ID}"
        HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
    
        # Create an MCP server instance.
        mcp = MCPServer("webex-mcp-lab-05")
    
    
        # The confirmation form the user sees: one boolean field.
        class Confirm(BaseModel):
            ok: bool
    
    
        # Resolver for address book deletion — always asks before proceeding.
        async def confirm_delete_book(address_book_id: str) -> Elicit[Confirm]:
            return Elicit(f"Delete address book '{address_book_id}'? This cannot be undone.", Confirm)
    
    
        # Resolver for entry deletion — always asks before proceeding.
        async def confirm_delete_entry(address_book_id: str, entry_id: str) -> Elicit[Confirm]:
            return Elicit(
                f"Delete entry '{entry_id}' from book '{address_book_id}'? This cannot be undone.",
                Confirm,
            )
    
    
        # Delete an address book after the user confirms via elicitation.
        @mcp.tool()
        async def delete_address_book(
            address_book_id: str,
            confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_delete_book)],
        ) -> dict:
            """Delete an address book by id. The server asks you to confirm first."""
            match confirm:
                case AcceptedElicitation(data=Confirm(ok=True)):
                    async with httpx.AsyncClient(timeout=15) as http:
                        r = await http.delete(
                            f"{ORG}/v3/address-book/{address_book_id}", headers=HEADERS
                        )
                    if r.status_code not in (200, 204):
                        return {"error": f"Webex Contact Center returned HTTP {r.status_code}."}
                    return {"deleted": True, "address_book_id": address_book_id}
                case AcceptedElicitation():
                    return {"deleted": False, "reason": "You chose not to delete."}
                case DeclinedElicitation() | CancelledElicitation():
                    return {"deleted": False, "reason": "Confirmation was declined or dismissed."}
    
    
        # Delete a single contact after the user confirms via elicitation.
        @mcp.tool()
        async def delete_entry(
            address_book_id: str,
            entry_id: str,
            confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_delete_entry)],
        ) -> dict:
            """Delete a single contact from an address book. The server asks you to confirm first."""
            match confirm:
                case AcceptedElicitation(data=Confirm(ok=True)):
                    async with httpx.AsyncClient(timeout=15) as http:
                        r = await http.delete(
                            f"{ORG}/v2/address-book/{address_book_id}/entry/{entry_id}",
                            headers=HEADERS,
                        )
                    if r.status_code not in (200, 204):
                        return {"error": f"Webex Contact Center returned HTTP {r.status_code}."}
                    return {"deleted": True, "entry_id": entry_id}
                case AcceptedElicitation():
                    return {"deleted": False, "reason": "You chose not to delete."}
                case DeclinedElicitation() | CancelledElicitation():
                    return {"deleted": False, "reason": "Confirmation was declined or dismissed."}
    
    
        # Start the server on stdio and wait for a client to connect.
        if __name__ == "__main__":
            print(
                "webex-mcp-lab-05 running on stdio - waiting for a client (Ctrl+C to stop).",
                file=sys.stderr,
            )
            mcp.run()
        ```

2. Update `.vscode/mcp.json` to include the new server, and start it:

    ```json
    {
      "servers": {
        "delete-books": {
          "command": "${workspaceFolder}/webexone/bin/python",
          "args": ["03_custom_mcp/05_delete_books.py"],
          "cwd": "${workspaceFolder}"
        }
      }
    } 
    ```

3. To test it, we will ask our agent to delete the Address Book we have just created using its ID:

    - Ask: *"Delete the address book with id 41e05f35-a2cd-4f3e-9d1b-3be7514080ce"*

4. The LLM itself asked us to confirm if we want to delete it:

    ![Approval Request](assets/delete_1.png){ width="450" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

5. Once you confirm, there is a request from VS Code for tool execution approval, as we got previously:

    ![Approval Request](assets/delete_2.png){ width="450" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

6. You will see another approval requested here which is what **Elicitation** means:

    ![Elicitation Approval](assets/delete_3.png){ width="450" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

    !!! Tip "Watch for"
        We got three approval moments. 
        
        - First, the LLM asked us to confirm the action.
        - Second, the MCP Client (VS Code) asks us to confirm tool execution.
        - Third, the MCP Server's elicitation form asks for final confirmation.
        
        They are different layers.

7. After you select `True`, book will be deleted:

    ![Elicitation Confirmation 1](assets/delete_4.png){ width="450" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

8. If you have connected the `read-books` MCP, you can confirm that the book is not listed anymore:

    - Ask: *"List my address books"*

    ![Delete Confirmation](assets/delete_5.png){ width="450" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

## Exercises

In this section, you can test your knowledge of what we have covered so far. If you need help, you can check the solution.

There is no official **Webex Calling** or **Control Hub troubleshooting** MCP server today. That is the gap a custom MCP server fills: you wrap the REST APIs you already used in Lab 2, register the server in VS Code (same as Lab 1), and ask the assistant in Chat.

Use the Service App token (`ACCESS_TOKEN`) from Lab 2. Follow the same pattern as `03_custom_mcp/03_read_books.py`: one tool per API, a short description, and a small JSON result the model can read.

### Relevant APIs

Use these as the starting catalog. You do not need to wrap all of them; pick a small set that answers a troubleshooting question.

#### Webex Calling

| API | What it is useful for | Documentation |
| --- | --- | --- |
| **Numbers** | List phone numbers in the org, see if they are assigned | [Numbers](https://developer.webex.com/calling/docs/api/v1/numbers){:target="_blank"} |
| **Locations** | Calling locations, which numbers and users belong where | [Locations](https://developer.webex.com/calling/docs/api/v1/locations){:target="_blank"} |
| **Location Call Settings** | Manage specific calling settings for a location | [Location Call Settings](https://developer.webex.com/calling/docs/api/v1/location-call-settings){:target="_blank"} |
| **Devices** | Phones and room devices registered in the org | [Devices](https://developer.webex.com/docs/api/v1/devices){:target="_blank"} |
| **Call Routing** | Dial plans, route groups, and routing choices | [Call Routing](https://developer.webex.com/calling/docs/api/v1/call-routing){:target="_blank"} |

#### Control Hub management

| API | What it is useful for | Documentation |
| --- | --- | --- |
| **People** | List users, licenses on a user, status | [People](https://developer.webex.com/admin/docs/api/v1/people){:target="_blank"} |
| **Licenses** | What the org is entitled to, and remaining counts | [Licenses](https://developer.webex.com/admin/docs/api/v1/licenses){:target="_blank"} |
| **Roles** | Admin roles available in the org | [Roles](https://developer.webex.com/admin/docs/api/v1/roles){:target="_blank"} |
| **Workspaces** | Meeting rooms and desk areas | [Workspaces](https://developer.webex.com/calling/docs/api/v1/workspaces){:target="_blank"} |

#### Troubleshooting / platform

| API | What it is useful for | Documentation |
| --- | --- | --- |
| **Webex Status** | Platform incidents before you blame the org | [Webex Status API](https://developer.webex.com/calling/docs/webex-status-api){:target="_blank"} |
| **Reports** | Usage and activity reports | [Reports](https://developer.webex.com/admin/docs/api/v1/reports){:target="_blank"} |
| **Detailed Call History** | Recent CDRs for a call-quality or “who called whom” investigation | [Detailed Call History](https://developer.webex.com/calling/docs/api/v1/reports-detailed-call-history){:target="_blank"} |
| **Admin Audit Events** | Who changed what in Control Hub | [Admin Audit Events](https://developer.webex.com/admin/docs/api/v1/admin-audit-events){:target="_blank"} |
| **Meeting Qualities** | Analytics and diagnostics for meetings | [Meeting Qualities](https://developer.webex.com/admin/docs/api/v1/meeting-qualities){:target="_blank"} |

### Build the MCP servers

- Create three new files, one for each domain:
    
    1. `03_custom_mcp/06_calling_mcp.py`
    2. `03_custom_mcp/07_control_hub_mcp.py`
    3. `03_custom_mcp/08_troubleshooting_mcp.py`

    Keep each tool small: call one endpoint, return a short JSON list (id, name, status), not the full raw payload.

    !!! Note "Note on Tool Complexity and Actions"
        For this exercise, you can focus on **listing** (read-only) operations only, to keep it simple and fast.

        The full versions are provided and used later in the lab.

??? Solution

    1. Create `03_custom_mcp/06_calling_mcp.py` and paste this code:

        ```python
        import logging
        import os
        import sys
        import httpx
        from dotenv import load_dotenv
        from mcp.server import MCPServer
    
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        log = logging.getLogger("calling-mcp")
    
        load_dotenv()
        TOKEN = os.environ.get("ACCESS_TOKEN")
    
        if not TOKEN:
            sys.exit("ACCESS_TOKEN is not set. Please set it in your .env file.")
    
        HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
    
        mcp = MCPServer("webex-calling-mcp")
    
        @mcp.tool()
        async def list_numbers(max_results: int = 25) -> dict:
            """List phone numbers configured in the organization."""
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.get(
                    "https://webexapis.com/v1/telephony/config/numbers",
                    headers=HEADERS,
                    params={"max": max_results}
                )
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            
            numbers = r.json().get("phoneNumbers", [])
            return {
                "count": len(numbers),
                "numbers": [
                    {"number": n.get("phoneNumber"), "state": n.get("state"), "location": n.get("location", {}).get("name")}
                    for n in numbers
                ]
            }
            
        @mcp.tool()
        async def list_locations(max_results: int = 10) -> dict:
            """List locations in the organization."""
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.get(
                    "https://webexapis.com/v1/locations",
                    headers=HEADERS,
                    params={"max": max_results}
                )
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            
            locations = r.json().get("items", [])
            return {
                "count": len(locations),
                "locations": [
                    {"id": l.get("id"), "name": l.get("name"), "address": l.get("address", {}).get("city")}
                    for l in locations
                ]
            }
        
        @mcp.tool()
        async def list_devices(max_results: int = 10) -> dict:
            """List devices in the organization."""
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.get(
                    "https://webexapis.com/v1/devices",
                    headers=HEADERS,
                    params={"max": max_results}
                )
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            
            devices = r.json().get("items", [])
            return {
                "count": len(devices),
                "devices": [
                    {"id": d.get("id"), "product": d.get("product"), "type": d.get("type"), "connectionStatus": d.get("connectionStatus")}
                    for d in devices
                ]
            }
            
        @mcp.tool()
        async def get_location_call_settings(location_id: str) -> dict:
            """Manage specific calling settings for a location."""
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.get(
                    f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callSettings",
                    headers=HEADERS
                )
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            
            return r.json()
    
        if __name__ == "__main__":
            log.info("webex-calling-mcp running on stdio - waiting for a client (Ctrl+C to stop).")
            try:
                mcp.run()
            except KeyboardInterrupt:
                log.info("Stopped.")
        ```

    2. Create `03_custom_mcp/07_control_hub_mcp.py` and paste this code:

        ```python
        import logging
        import os
        import sys
        import httpx
        from dotenv import load_dotenv
        from mcp.server import MCPServer
    
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        log = logging.getLogger("control-hub-mcp")
    
        load_dotenv()
        TOKEN = os.environ.get("ACCESS_TOKEN")
    
        if not TOKEN:
            sys.exit("ACCESS_TOKEN is not set. Please set it in your .env file.")
    
        HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
    
        mcp = MCPServer("webex-control-hub-mcp")
    
        @mcp.tool()
        async def list_people(max_results: int = 10) -> dict:
            """List users (people) in the organization."""
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.get(
                    "https://webexapis.com/v1/people",
                    headers=HEADERS,
                    params={"max": max_results}
                )
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            
            people = r.json().get("items", [])
            return {
                "count": len(people),
                "people": [
                    {"id": p.get("id"), "emails": p.get("emails"), "displayName": p.get("displayName")}
                    for p in people
                ]
            }
            
        @mcp.tool()
        async def list_workspaces(max_results: int = 10) -> dict:
            """List workspaces in the organization."""
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.get(
                    "https://webexapis.com/v1/workspaces",
                    headers=HEADERS,
                    params={"max": max_results}
                )
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            
            workspaces = r.json().get("items", [])
            return {
                "count": len(workspaces),
                "workspaces": [
                    {"id": w.get("id"), "displayName": w.get("displayName"), "type": w.get("type")}
                    for w in workspaces
                ]
            }
        
        @mcp.tool()
        async def list_licenses() -> dict:
            """List licenses in the organization."""
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.get(
                    "https://webexapis.com/v1/licenses",
                    headers=HEADERS
                )
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            
            licenses = r.json().get("items", [])
            return {
                "count": len(licenses),
                "licenses": [
                    {"id": l.get("id"), "name": l.get("name"), "consumedUnits": l.get("consumedUnits"), "totalUnits": l.get("totalUnits")}
                    for l in licenses
                ]
            }
            
        @mcp.tool()
        async def list_roles(max_results: int = 20) -> dict:
            """List admin roles available in the organization."""
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.get(
                    "https://webexapis.com/v1/roles",
                    headers=HEADERS,
                    params={"max": max_results}
                )
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            
            roles = r.json().get("items", [])
            return {
                "count": len(roles),
                "roles": [
                    {"id": role.get("id"), "name": role.get("name"), "description": role.get("description")}
                    for role in roles
                ]
            }
    
        if __name__ == "__main__":
            log.info("webex-control-hub-mcp running on stdio - waiting for a client (Ctrl+C to stop).")
            try:
                mcp.run()
            except KeyboardInterrupt:
                log.info("Stopped.")
        ```

    3. Create `03_custom_mcp/08_troubleshooting_mcp.py` and paste this code:

        ```python
        import logging
        import os
        import sys
        import httpx
        from datetime import datetime, timedelta, timezone
        from dotenv import load_dotenv
        from mcp.server import MCPServer
    
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        log = logging.getLogger("troubleshooting-mcp")
        
        load_dotenv()
        TOKEN = os.environ.get("ACCESS_TOKEN")
        ORG_ID = os.environ.get("WEBEX_ORG_ID")
        
        if not TOKEN or not ORG_ID:
            sys.exit("ACCESS_TOKEN and WEBEX_ORG_ID must be set in your .env file.")
        
        HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
    
        mcp = MCPServer("webex-troubleshooting-mcp")
    
        @mcp.tool()
        async def unresolved_incidents() -> dict:
            """Check Webex for any unresolved platform incidents."""
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.get("https://status.webex.com/api/v2/incidents/unresolved.json")
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            
            incidents = r.json().get("incidents", [])
            return {"count": len(incidents), "incidents": incidents}
            
        @mcp.tool()
        async def list_admin_audit_events(days_back: int = 7, max_results: int = 10) -> dict:
            """List recent admin audit events in the organization."""
            now = datetime.now(timezone.utc)
            past = now - timedelta(days=days_back)
            
            params = {
                "orgId": ORG_ID,
                "from": past.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "to": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "max": max_results
            }
            
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.get(
                    "https://webexapis.com/v1/adminAudit/events",
                    headers=HEADERS,
                    params=params
                )
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            
            events = r.json().get("items", [])
            return {
                "count": len(events),
                "events": [
                    {"id": e.get("id"), "actionText": e.get("actionText"), "actorOrgName": e.get("actorOrgName"), "created": e.get("created")}
                    for e in events
                ]
            }
            
        @mcp.tool()
        async def list_reports() -> dict:
            """List recent usage and activity reports generated in the organization."""
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.get(
                    "https://webexapis.com/v1/reports",
                    headers=HEADERS
                )
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            
            reports = r.json().get("items", [])
            return {
                "count": len(reports),
                "reports": [
                    {"id": rep.get("Id"), "title": rep.get("title"), "status": rep.get("status")}
                    for rep in reports
                ]
            }
            
        @mcp.tool()
        async def get_meeting_qualities(meeting_id: str) -> dict:
            """Analytics and diagnostics for meetings."""
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.get(
                    f"https://webexapis.com/v1/meeting/qualities?meetingId={meeting_id}",
                    headers=HEADERS
                )
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            
            return r.json()
    
        if __name__ == "__main__":
            log.info("webex-troubleshooting-mcp running on stdio - waiting for a client (Ctrl+C to stop).")
            try:
                mcp.run()
            except KeyboardInterrupt:
                log.info("Stopped.")
        ```

### Register the servers in your IDE

- Add your new servers to `.vscode/mcp.json` the same way you did in Step 3.2, start them, and confirm tools are discovered in the Output view.

??? Solution

    1. Open `.vscode/mcp.json` and add the new server configurations:

        ```json
        {
          "servers": {
            "calling-mcp": {
              "command": "${workspaceFolder}/webexone/bin/python",
              "args": ["03_custom_mcp/06_calling_mcp.py"],
              "cwd": "${workspaceFolder}"
            },
            "control-hub-mcp": {
              "command": "${workspaceFolder}/webexone/bin/python",
              "args": ["03_custom_mcp/07_control_hub_mcp.py"],
              "cwd": "${workspaceFolder}"
            },
            "troubleshooting-mcp": {
              "command": "${workspaceFolder}/webexone/bin/python",
              "args": ["03_custom_mcp/08_troubleshooting_mcp.py"],
              "cwd": "${workspaceFolder}"
            }
          }
        }
        ```

    2. Reload the window if needed (`Developer: Reload Window`).
    3. Open the Command Palette (`Ctrl+Shift+P`), type **MCP: List Servers**, select each server, and click **Start Server**.
    4. In Output you should see tools discovered for each of them.

        ![List Servers](assets/placeholder_list_servers.png){ width="650" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

### Test the MCP Servers

#### Test in VS Code

In Chat, ask a question that needs **multiple** tools across different servers, so the assistant has to chain them. For example:

- Ask: "*List the phone numbers in this organization. Then tell me how many users we have, and whether Webex has any unresolved incidents.*"

??? Solution

    1. Open **Chat: Open Chat (Agent)** and make sure your custom servers are attached.
    2. Ask the question in natural language. You should see tool calls (`list_numbers`, then `list_people`, then `unresolved_incidents`).
    3. Allow the tools when VS Code prompts.
    4. The final answer should be written by the LLM from the tool results, not a hardcoded string.

        ![Chat Tools](assets/placeholder_chat_tools.png){ width="650" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

        !!! Warning
            If a tool returns `403`, the Service App is missing a scope. You will need to add the following scopes to your Service App in the Webex Developer Portal, authorize it again, generate a new token, update `.env`, and restart the servers:
            
            - `spark-admin:telephony_config_read` (for Calling numbers/locations)
            - `spark-admin:devices_read` (for Calling devices)
            - `spark-admin:people_read` (for Control Hub people)
            - `spark-admin:workspaces_read` (for Control Hub workspaces)
            - `spark-admin:licenses_read` (for Control Hub licenses)
            - `spark-admin:roles_read` (for Control Hub roles)
            - `spark-admin:admin_audit_events_read` (for Troubleshooting audit events)

#### Test with MCP Inspector (Optional)

You can also test each of these servers in isolation using the MCP Inspector, just as you did before:

1. In your terminal, run the inspector for the Calling MCP:
   ```bash
   npx @modelcontextprotocol/inspector python 03_custom_mcp/06_calling_mcp.py
   ```
2. Connect in the browser, list tools, and test them.
3. Repeat for `07_control_hub_mcp.py` and `08_troubleshooting_mcp.py`.
