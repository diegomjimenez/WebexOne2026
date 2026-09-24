# Lab 3 - Webex APIs

In the previous section, we enabled our agent to use MCP servers to perform actions on our behalf. The assistant called Webex for you through the official MCP servers, and each of those servers is just a wrapper around Webex API calls.

In this section you will make those API calls yourself. This matters because the official MCP servers cover only a limited set of APIs, and we want to give our agent more tools and possibilities. That is what we will build in the next labs.

## Step 3.1 - Get a Personal Access Token

During the previous lab, you used an **Agentic MCP App token** to perform actions. That is a special token, scoped to execute actions through the MCP servers, and it only works with the official Webex MCP servers. It will not work for the direct API calls in this lab.

For the simplicity of this hands-on lab, we will use your Personal Access Token (PAT) instead. Because you are an administrator in this sandbox, your PAT automatically inherits all your admin rights. It requires no scope configuration and lasts for 12 hours, which is perfect for a workshop.

1. In [Webex for Developers](https://developer.webex.com/){:target="_blank"}, in the top right corner, click your avatar and select copy the **Bearer** token.

    ![Token](./assets/token_6.png){ width="350" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

2. Open the `.env` file at the root of your project (you copied it from `.env.example` in Getting Started), paste the token and save the file:

    ```env
    ACCESS_TOKEN=
    ```

3. Paste the same token into the `token` variable of your Bruno environment, so your requests can use `Bearer {{token}}` and save.

    ![Token](./assets/token_7.png){ width="750" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

## Step 3.2: Production Architecture (Service Apps & Integrations)

While a Personal Access Token is perfect for a quick lab, it has a major problem for production: **It expires after 12 hours**. That is not valid for a bot that should keep running forever.

That is what **Service Apps** and **OAuth Integrations** are for.

### What is a Service App?

A Service App is a Webex integration for **machine-to-machine** communication.

Unlike a Personal Access Token (which acts on behalf of *you*), a Service App has no user context. It acts as a system or background service. That is the usual choice for administrative tasks and compliance in production.

### Tokens and Scopes

You have already seen how scopes work. When we looked at the [Meetings MCP Server documentation](https://developer.webex.com/mcp/docs/meetings-mcp-server), the MCP token was a wrapper around specific permissions (like `meeting:schedules_read` or `meeting:schedules_write`).

![Scope](./assets/scope_1.png){ width="850" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

Every Webex API requires specific scopes. How you get those scopes depends on the token type:

1. **Personal Access Token (what we are using):** The Developer Token you just copied inherits *all* the scopes your user account has. Since you are an admin, it has admin scopes.
2. **Service Apps (production):** When you create a Service App, you must explicitly define its **scopes** to limit what the machine is allowed to do. If it needs to connect to an official Webex MCP Server, it must include the `spark:mcp` scope, alongside any other API scopes the tools require.

![Scope](./assets/scope_3.png){ width="450" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

### User Context vs. Machine Context

A Service App token is still a standard Webex OAuth 2.0 Bearer token, so you can pass it to an MCP server the same way you passed a PAT. However, the APIs do not behave the same:

1. **Personal Access Token (User Context):**
   When you used your token with the `webex-list-meetings` MCP tool, the Webex API knew *who* was asking. It fetched *your* meetings.

2. **Service App Token (Machine Context):**
   A Service App is a faceless machine. If it calls `webex-list-meetings` without specifying a user, the API will likely return an empty list because the machine itself does not have a calendar.

!!! Warning "Analytics and Reports"
    Service Apps work for most administrative tasks. Webex Analytics and Reporting APIs require **user context** — they block Service Apps by design.

    If a production AI assistant needs to pull analytics or reports, it cannot use a Service App. It uses an **OAuth Integration**: the bot sends the user a "Log In" button, the human admin logs in, and the bot receives a user-bound token.

### Service Apps

Because a Service App operates at machine level and can access organization-wide data, a Webex administrator must review the requested scopes and authorize the app in Control Hub before it can generate tokens.

For this lab we skip that process. Everything from here on uses your Personal Access Token.

??? Note "Reference: How to Create and approve a Service App"
    If you ever need a Service App in production, here is how you do it:

    1. Log into [developer.webex.com](https://developer.webex.com/){:target="_blank"}.
    2. In the top right corner of the page, click your avatar and then select [My Webex Apps](https://developer.webex.com/my-apps){:target="_blank"}.
    3. Click **Create a New App**.
    4. On the ‘Create a New App’ page, find the Service App card and click the ‘Create a Service App’ button.

        ![Service App](./assets/bot_1.png){ width="850" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }

    5. Enter the necessary information (Name, Icon, Description, Contact Email).
    6. Select the **Scopes** your machine needs. For example, to read phone numbers, you would need `spark-admin:telephony_config_read`.

        ![Service App](./assets/serviceapp_1.png){ style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    7. Once created, you will get a **Client ID** and **Client Secret**.

        ![Service App](./assets/serviceapp_2.png){ style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    8. At the top, in the `Admin Authorization` section, click on **Request admin authorization**.

        ![Service App](./assets/serviceapp_3.png){ width="600" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    9. A Webex Administrator must then go to **Collaboration Control Hub** -> **Apps** -> **Service Apps**, select your app, and click **Authorize**.

        ![Service App](./assets/serviceapp_4.png){ style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    10. Finally, you return to the Developer Portal, select your Org under **Org Authorizations**, enter your Client Secret, and click **Generate tokens** to get your 14-day `access_token` and 90-day `refresh_token`.

        ![Service App](./assets/serviceapp_5.png){ width="800" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}
        ![Service App](./assets/serviceapp_6.png){ width="800" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    **How to Refresh a Service App Token**

    Unlike a Personal Access Token which simply expires, a Service App token can be refreshed using the `refresh_token`. That is just another Webex API call: a form-encoded `POST` to `https://webexapis.com/v1/access_token` with these fields:

    | Field | Value |
    | --- | --- |
    | `grant_type` | `refresh_token` |
    | `client_id` | The Client ID from the Service App |
    | `client_secret` | The Client Secret from the Service App |
    | `refresh_token` | The 90-day refresh token generated above |

    The response returns a new `access_token` and a new `refresh_token`. Store both; the previous refresh token is no longer valid.

    The Developer Portal has the same request, with snippets in the language you need: [Using the Refresh Token](https://developer.webex.com/create/docs/authentication#using-the-refresh-token){:target="_blank"}.

    ??? Tip "Python Code" 
        ```python
        import requests
    
        url = "https://webexapis.com/v1/access_token"
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': 'YOUR_REFRESH_TOKEN',
            'client_id': 'YOUR_CLIENT_ID',
            'client_secret': 'YOUR_CLIENT_SECRET',
        }
        headers = {
            'Content-type': 'application/x-www-form-urlencoded'
        }
    
        response = requests.post(url, headers=headers, data=payload)
        print(response.json()) # Contains the new access_token and refresh_token
        ```

## Step 3.3: Calling Webex APIs

Now that we have our token, we can start making API calls. The [Webex Developer Portal](https://developer.webex.com/docs/api/v1/){:target="_blank"} provides documentation and ready-to-use code snippets for all APIs. You can select your preferred language (cURL, Python and Node.js) and copy the code directly.

Every Webex API call has the same anatomy: a method, a URL, and an `Authorization` header carrying your token. Once you have seen that, the tool you use is a matter of what you are trying to do:

| Tool | What we will use it for |
| --- | --- |
| **cURL** | A quick check from the terminal. No setup, and it is what you paste into a ticket so a colleague can reproduce your result. |
| **Bruno** | Exploring an API properly: saved requests, the token in an environment variable, and IDs from one response feeding the next. |
| **Python** | The form an assistant needs. This is the shape your Lab 4 MCP tools take. |

### Calling APIs using cURL

Start with the smallest possible call: who does this token belong to?

!!! Warning
    Replace `YOUR_ACCESS_TOKEN` with the token from your `.env` file.

1. Run the following command from the **VS Code terminal**:

    ```bash
    curl -s -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://webexapis.com/v1/people/me" | python -m json.tool
    ```

    The response is your own user record:

    ??? Tip "Full response"
        ```powershell
        (webexone)  % curl -s -H "Authorization: Bearer MzY5NzViMTAtOWM0ZS00ZGIwLTllOWItNGQ4ZGMzYmQ5YzUwNDkzMGNiNTYtYmRj_P0A1_74983fd5-5c18-45cb-bfcd-507005e05b0f" "https://webexapis.com/v1/people/me" | python -m json.tool
        {
            "id": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xOGMyYzQ4OS0yZmVmLTRhMTUtYTRiZC1jYWI3YjY1ZDg0MTY",
            "emails": [
                "pod0@webexone-ai-assistant.wbx.ai"
            ],
            "sipAddresses": [
                {
                    "type": "cloud-calling",
                    "value": "pod0@webexone-ai-assistant-sbx.calls.webex.com",
                    "primary": true
                }
            ],
            "displayName": "Pod 0",
            "nickName": "Pod",
            "firstName": "Pod",
            "lastName": "0",
            "orgId": "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi83NDk4M2ZkNS01YzE4LTQ1Y2ItYmZjZC01MDcwMDVlMDViMGY",
            "roles": [
                "Y2lzY29zcGFyazovL3VzL1JPTEUvaWRfZnVsbF9hZG1pbg"
            ],
            "licenses": [
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZUTV9mNWZkZTM1Zi00NzA0LTQ2MGEtODEwZi00YzVkMzUyNDFlNjk",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZTU18xYjcyOGZmOS03ZGU4LTRjYjctOTU0MC0yOTMyMGI1YTQyY2I",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZNU185ZWNhNzgxNC0zMzEzLTQ2NGYtOTY0Mi0wMjM5ODc1YmM5Zjg",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZUQ19hMjQ3MzgyOC1hOTgwLTQ3MmYtODE5ZC02YjljY2UwOGU5MmI"
            ],
            "created": "2026-09-23T10:06:45.423Z",
            "lastModified": "2026-09-23T10:08:45.930Z",
            "status": "unknown",
            "invitePending": false,
            "loginEnabled": true,
            "type": "person",
            "siteUrls": [
                "webexone-ai-assistant-sbx.webex.com"
            ]
        }
        ```

    !!! Warning
        If this returns `401`, your token is wrong or expired, and no call will work.
    
2. Now something only an administrator can ask — what is the organization entitled to?

    ```bash
    curl -s -H "Authorization: Bearer YOUR_ACCESS_TOKEN" "https://webexapis.com/v1/licenses" | python -m json.tool
    ```

    ??? Tip "Full response"
        ```powershell
        {
            "items": [
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkVQQ19mZDdjNmNkMC0zZWRhLTRkYTUtOWNmZC0yZjVhNGJhMzZlNDk",
                    "name": "Epic Desktop Connector for Webex Contact Center",
                    "totalUnits": 10,
                    "consumedUnits": 0,
                    "consumedByUsers": 0,
                    "consumedByWorkspaces": 0,
                    "subscriptionId": "trialSub.e57285a3-275b-4547-ae16-69d6371cc2c0"
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOk1TX2ZkY2E5ZDBkLTJkZmEtNDM5Yi04MmM4LTUzMDU3MGVjOWY1Yw",
                    "name": "Advanced Messaging",
                    "totalUnits": 100,
                    "consumedUnits": 1,
                    "consumedByUsers": 1,
                    "consumedByWorkspaces": 0,
                    "subscriptionId": "trialSub.e57285a3-275b-4547-ae16-69d6371cc2c0"
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOlNGRFNLX2VhMThiNzZmLTE2MzQtNGM5Ny05NWQwLTg0MjFjODBmYzkxYg",
                    "name": "Salesforce Desktop Connector",
                    "totalUnits": 10,
                    "consumedUnits": 0,
                    "consumedByUsers": 0,
                    "consumedByWorkspaces": 0,
                    "subscriptionId": "trialSub.e57285a3-275b-4547-ae16-69d6371cc2c0"
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkJDUkxDXzRkNTFkZWMxLTU2MDItNDRmZS04ZTgyLWQ1ZDliZTIzOGY0ZQ",
                    "name": "Webex Calling - Route List Calls",
                    "totalUnits": 10,
                    "consumedUnits": 0,
                    "consumedByUsers": null,
                    "consumedByWorkspaces": null,
                    "subscriptionId": "trialSub.e57285a3-275b-4547-ae16-69d6371cc2c0"
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkNKUFBSTV9kOTJmMDcxNi00MzM1LTRjYzEtOWYyOC1iODJiZmVmMTRmMzM",
                    "name": "Contact Center Premium Agent",
                    "totalUnits": 50,
                    "consumedUnits": 3,
                    "consumedByUsers": 3,
                    "consumedByWorkspaces": 0,
                    "subscriptionId": "trialSub.e57285a3-275b-4547-ae16-69d6371cc2c0"
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOlNEX2YwOTk5YTY0LTNiMWEtNDUxOS1iYWNjLTg1OGVlN2U1NjczNA",
                    "name": "Webex Room Kit",
                    "totalUnits": 5,
                    "consumedUnits": 0,
                    "consumedByUsers": 0,
                    "consumedByWorkspaces": 0,
                    "subscriptionId": "trialSub.e57285a3-275b-4547-ae16-69d6371cc2c0"
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkVFXzRkZDBjMWUwLTdhYWUtNDhjZi1iYTQzLTM2M2MxM2RlNDMwYl93ZWJleG9uZS1haS1hc3Npc3RhbnQtc2J4LndlYmV4LmNvbQ",
                    "name": "Webex Meetings Suite",
                    "totalUnits": 100,
                    "consumedUnits": 3,
                    "consumedByUsers": 3,
                    "consumedByWorkspaces": 0,
                    "siteUrl": "webexone-ai-assistant-sbx.webex.com",
                    "siteType": "Control Hub managed site",
                    "subscriptionId": "trialSub.e57285a3-275b-4547-ae16-69d6371cc2c0"
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkJDU1REXzdiNzk3N2QxLTQ2MzQtNDJlZS1iMzIwLWY0NDc4NDFkODdiYg",
                    "name": "Webex Calling - Professional",
                    "totalUnits": 100,
                    "consumedUnits": 3,
                    "consumedByUsers": 2,
                    "consumedByWorkspaces": 1,
                    "subscriptionId": "trialSub.e57285a3-275b-4547-ae16-69d6371cc2c0"
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkJDQ0FfMWNhZWYxNjYtMjExMy00NGQ1LWJlMzUtZWNkMDk3OTgwODAx",
                    "name": "Webex Calling - Workspaces",
                    "totalUnits": 100,
                    "consumedUnits": 0,
                    "consumedByUsers": 0,
                    "consumedByWorkspaces": 0,
                    "subscriptionId": "trialSub.e57285a3-275b-4547-ae16-69d6371cc2c0"
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkNKUFNURF8xN2Y5YTMwOC03OTgyLTRiNmQtYjVlMC0xZTZiM2MyMjMxNzM",
                    "name": "Contact center Standard Agent",
                    "totalUnits": 50,
                    "consumedUnits": 0,
                    "consumedByUsers": 0,
                    "consumedByWorkspaces": 0,
                    "subscriptionId": "trialSub.e57285a3-275b-4547-ae16-69d6371cc2c0"
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOlJUVF9lZWVjNGQ2ZC0wNTFhLTRiMjAtODIzNi0xZDM0YWQyYzU3MzQ",
                    "name": "Real-Time Translations",
                    "totalUnits": 100,
                    "consumedUnits": 3,
                    "consumedByUsers": 3,
                    "consumedByWorkspaces": 0,
                    "subscriptionId": "trialSub.e57285a3-275b-4547-ae16-69d6371cc2c0"
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkNGXzQzNWIzZGYxLWI3NDYtNGE2MS04Y2Y5LTc4M2RlOWNjY2ZiZA",
                    "name": "Advanced Space Meetings",
                    "totalUnits": 100,
                    "consumedUnits": 1,
                    "consumedByUsers": 1,
                    "consumedByWorkspaces": 0,
                    "subscriptionId": "trialSub.e57285a3-275b-4547-ae16-69d6371cc2c0"
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkJDSERPX2ZmNTZmMTcwLThlZDAtMzE2OC04YWMwLWRmMWJjNGViMDA4Mw",
                    "name": "Webex Calling - Hot desk only",
                    "totalUnits": 9,
                    "consumedUnits": 0,
                    "consumedByUsers": 0,
                    "consumedByWorkspaces": 0
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkNFXzEyM2UzNTY2LTVlMDYtNGJmMy04NDQ5LTFhYjUxYTFkMWNlMw",
                    "name": "Hybrid - Exchange Calendar",
                    "totalUnits": 44,
                    "consumedUnits": 0,
                    "consumedByUsers": 0,
                    "consumedByWorkspaces": 0
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkNHXzVkYjcwNjYyLWNmYTItNGFjZC04MTRlLTgwYjNiNWVkZjNlZA",
                    "name": "Hybrid - Google Calendar",
                    "totalUnits": 44,
                    "consumedUnits": 0,
                    "consumedByUsers": 0,
                    "consumedByWorkspaces": 0
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZNU185ZWNhNzgxNC0zMzEzLTQ2NGYtOTY0Mi0wMjM5ODc1YmM5Zjg",
                    "name": "Basic Messaging",
                    "totalUnits": 44,
                    "consumedUnits": 44,
                    "consumedByUsers": 44,
                    "consumedByWorkspaces": 0
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZTU18xYjcyOGZmOS03ZGU4LTRjYjctOTU0MC0yOTMyMGI1YTQyY2I",
                    "name": "Free screen share",
                    "totalUnits": 44,
                    "consumedUnits": 44,
                    "consumedByUsers": 44,
                    "consumedByWorkspaces": 0
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZUQ19hMjQ3MzgyOC1hOTgwLTQ3MmYtODE5ZC02YjljY2UwOGU5MmI",
                    "name": "Call on Webex (1:1 call, non-PSTN)",
                    "totalUnits": 44,
                    "consumedUnits": 44,
                    "consumedByUsers": 44,
                    "consumedByWorkspaces": 0
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZUTV9mNWZkZTM1Zi00NzA0LTQ2MGEtODEwZi00YzVkMzUyNDFlNjk",
                    "name": "Basic Space Meetings",
                    "totalUnits": 44,
                    "consumedUnits": 44,
                    "consumedByUsers": 44,
                    "consumedByWorkspaces": 0
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkhNXzdjOGMyZGVhLWIwNTUtNDNlNy1hODkyLWNmMmI1MDcyNTAzNg",
                    "name": "Hybrid - Message",
                    "totalUnits": 44,
                    "consumedUnits": 0,
                    "consumedByUsers": 0,
                    "consumedByWorkspaces": 0
                },
                {
                    "id": "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOlVDUFJFTV9jMzMyOWQzMi0xNmVkLTQxNDUtOTUyNS02M2FjYjRiMzFiMjA",
                    "name": "Unified Communication Manager (UCM)",
                    "totalUnits": 44,
                    "consumedUnits": 0,
                    "consumedByUsers": 0,
                    "consumedByWorkspaces": 0
                }
            ]
        }
        ```

Two commands in, and you have already proved both halves of what you need: the token is valid, and it carries admin rights.

### Calling APIs using Bruno

cURL is fine for one-off checks, but it gets painful as soon as you want to keep a call, tweak its parameters, or reuse an ID from a previous response. That is where Bruno comes in.

To demonstrate Control Hub management capabilities, we will use the **Numbers API** to list the phone numbers configured in the organization. This is a typical administrative task.

1. In the `WebexOne` collection you created in Getting Started, add a new `HTTP GET` request called `List Numbers`:

    ![Bruno](./assets/bruno_4.png){ width="350" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

2. Set the URL to: `https://webexapis.com/v1/telephony/config/numbers`
3. Go to the **Headers** tab and add:

    | Header | Value |
    | --- | --- |
    | `Authorization` | `Bearer {{token}}`|

    !!! Note
        `{{token}}` reads the token from your Bruno environment.

    ![Bruno](./assets/bruno_5.png){ width="550" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}
   
4. Click **Send**. You should get the phone numbers in the organization, each with its state and location:

    ![Bruno](./assets/bruno_6.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

Now add a second request, and use a query parameter to keep the response small:

5. Clone the request, rename it `List Locations`, and set the URL to `https://webexapis.com/v1/telephony/config/locations`:

    ![Bruno](./assets/bruno_7.png){ width="450" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

6.  Open the **Params** tab and add a query parameter `max` with value `1`, then **Send**.

    ![Bruno](./assets/bruno_8.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

Finally, chain the two calls. Most troubleshooting work looks like this: one call gives you an ID, and the next call needs it.

7. From the locations response, copy the `id` of one location and go to the `Enviroment`:

    ![Bruno](./assets/bruno_9.png){ width="350" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

8. Add it to your environment as a variable called `locationId` and `Save`:

    ![Bruno](./assets/bruno_10.png){ width="750" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

9. Create one more request, `Get Location`, with the URL `https://webexapis.com/v1/telephony/config/locations/{{locationId}}`, and **Send**.

    ![Bruno](./assets/bruno_11.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

You now have the calling configuration of a single location: its announcement language, its calling line ID, and so on. Notice that this detail was not in the list response — you had to ask for it specifically, with an ID you obtained from an earlier call.

??? Tip "Let Bruno capture the id"
    Bruno can store that `id` for you, so you do not copy it by hand. On the `List Locations` request, open the **Script** tab, choose **Post Response**, and paste:

    ```javascript
    const locations = res.getBody().locations;
    if (locations && locations.length) {
      bru.setEnvVar("locationId", locations[0].id);
    }
    ```

    Send `List Locations` again. `{{locationId}}` is now set in the environment, and `Get Location` can use it immediately:

    ![Bruno](./assets/bruno_12.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    That script is still glue you wrote: you had to know the field is called `locations`, that `id` is the one to keep, and that the next URL needs it. Later in the lab, the agent will make that choice on its own.

### Calling APIs using Python

Bruno is where you explore an API. Code is how you automate it once you know it works. To close this step, we will list the users in the organization from a Python script.

First, see where this snippet comes from:

1. Open the [List People](https://developer.webex.com/admin/docs/api/v1/people/list-people){:target="_blank"} reference in the Developer Portal.
2. In the code panel on the right, switch the language selector to **Python**. The portal generates a ready-to-run snippet for the endpoint you are reading about, with your own token filled in:

    ![Developer](./assets/developer_1.png){ width="700" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

3. Navigate to `03_webex_apis/01_list_people.py`. This file contains the request but reading the token from `.env` instead of hardcoding it:

    ??? Tip "Python Code"
        ```python
        # Step 01 - list people in the organization. Same shape as the Developer Portal snippet, token from .env.
        
        import json
        import os
        import sys
        import requests
        from dotenv import load_dotenv
        
        load_dotenv()
        token = os.getenv("ACCESS_TOKEN")
        
        if not token:
            sys.exit("ACCESS_TOKEN is not set. Copy it into your .env file (see Getting Started).")
        
        url = "https://webexapis.com/v1/people"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(url, headers=headers, params={"max": 5})
        print(json.dumps(response.json(), indent=2))
        ```

4. In VS Code, make sure your terminal is in the correct folder:

    * cd 03_webex_apis

5. Run the script:

    * python 01_list_people.py
    
6. You should receive a JSON response containing a list of people in your organization.

    ??? Note "Full response"
        ```json
        {
          "notFoundIds": null,
          "items": [
            {
              "id": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS9lNmEzMGMyNi1hNTBmLTQxODAtODM4MS0yNDIyZGNhOWYwMjc",
              "emails": [
                "admin@webexone-ai-assistant.wbx.ai"
              ],
              "sipAddresses": [
                {
                  "type": "personal-room",
                  "value": "26627884171@webexone-ai-assistant-sbx.webex.com",
                  "primary": false
                },
                {
                  "type": "personal-room",
                  "value": "admin61@webexone-ai-assistant-sbx.webex.com",
                  "primary": false
                },
                {
                  "type": "cloud-calling",
                  "value": "admin@webexone-ai-assistant-sbx.calls.webex.com",
                  "primary": true
                }
              ],
              "displayName": "admin@webexone-ai-assistant.wbx.ai",
              "nickName": "admin",
              "firstName": "admin",
              "lastName": "admin",
              "orgId": "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi83NDk4M2ZkNS01YzE4LTQ1Y2ItYmZjZC01MDcwMDVlMDViMGY",
              "roles": [
                "Y2lzY29zcGFyazovL3VzL1JPTEUvaWRfZnVsbF9hZG1pbg"
              ],
              "licenses": [
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkNKUFBSTV9kOTJmMDcxNi00MzM1LTRjYzEtOWYyOC1iODJiZmVmMTRmMzM",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkVFXzRkZDBjMWUwLTdhYWUtNDhjZi1iYTQzLTM2M2MxM2RlNDMwYl93ZWJleG9uZS1haS1hc3Npc3RhbnQtc2J4LndlYmV4LmNvbQ",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOk1TX2ZkY2E5ZDBkLTJkZmEtNDM5Yi04MmM4LTUzMDU3MGVjOWY1Yw",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZUQ19hMjQ3MzgyOC1hOTgwLTQ3MmYtODE5ZC02YjljY2UwOGU5MmI",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkNGXzQzNWIzZGYxLWI3NDYtNGE2MS04Y2Y5LTc4M2RlOWNjY2ZiZA",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZUTV9mNWZkZTM1Zi00NzA0LTQ2MGEtODEwZi00YzVkMzUyNDFlNjk",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZTU18xYjcyOGZmOS03ZGU4LTRjYjctOTU0MC0yOTMyMGI1YTQyY2I",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOlJUVF9lZWVjNGQ2ZC0wNTFhLTRiMjAtODIzNi0xZDM0YWQyYzU3MzQ",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZNU185ZWNhNzgxNC0zMzEzLTQ2NGYtOTY0Mi0wMjM5ODc1YmM5Zjg"
              ],
              "created": "2026-09-14T08:42:42.096Z",
              "lastModified": "2026-09-23T10:07:18.779Z",
              "lastActivity": "2026-09-23T10:08:58.494Z",
              "status": "inactive",
              "invitePending": false,
              "loginEnabled": true,
              "type": "person",
              "siteUrls": [
                "webexone-ai-assistant-sbx.webex.com"
              ]
            },
            {
              "id": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xOGMyYzQ4OS0yZmVmLTRhMTUtYTRiZC1jYWI3YjY1ZDg0MTY",
              "emails": [
                "pod0@webexone-ai-assistant.wbx.ai"
              ],
              "sipAddresses": [
                {
                  "type": "cloud-calling",
                  "value": "pod0@webexone-ai-assistant-sbx.calls.webex.com",
                  "primary": true
                }
              ],
              "displayName": "Pod 0",
              "nickName": "Pod",
              "firstName": "Pod",
              "lastName": "0",
              "orgId": "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi83NDk4M2ZkNS01YzE4LTQ1Y2ItYmZjZC01MDcwMDVlMDViMGY",
              "roles": [
                "Y2lzY29zcGFyazovL3VzL1JPTEUvaWRfZnVsbF9hZG1pbg"
              ],
              "licenses": [
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZUTV9mNWZkZTM1Zi00NzA0LTQ2MGEtODEwZi00YzVkMzUyNDFlNjk",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZTU18xYjcyOGZmOS03ZGU4LTRjYjctOTU0MC0yOTMyMGI1YTQyY2I",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZNU185ZWNhNzgxNC0zMzEzLTQ2NGYtOTY0Mi0wMjM5ODc1YmM5Zjg",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZUQ19hMjQ3MzgyOC1hOTgwLTQ3MmYtODE5ZC02YjljY2UwOGU5MmI"
              ],
              "created": "2026-09-23T10:06:45.423Z",
              "lastModified": "2026-09-23T10:08:45.930Z",
              "status": "unknown",
              "invitePending": false,
              "loginEnabled": true,
              "type": "person",
              "siteUrls": [
                "webexone-ai-assistant-sbx.webex.com"
              ]
            },
            {
              "id": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS9kNWY3ZTBmZi1mMGZiLTRjNWUtYTE2Zi02YzBmNmRmMzc1YzY",
              "emails": [
                "pod10@webexone-ai-assistant.wbx.ai"
              ],
              "sipAddresses": [
                {
                  "type": "cloud-calling",
                  "value": "pod10@webexone-ai-assistant-sbx.calls.webex.com",
                  "primary": true
                }
              ],
              "displayName": "Pod 10",
              "nickName": "Pod",
              "firstName": "Pod",
              "lastName": "10",
              "orgId": "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi83NDk4M2ZkNS01YzE4LTQ1Y2ItYmZjZC01MDcwMDVlMDViMGY",
              "roles": [
                "Y2lzY29zcGFyazovL3VzL1JPTEUvaWRfZnVsbF9hZG1pbg"
              ],
              "licenses": [
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZUTV9mNWZkZTM1Zi00NzA0LTQ2MGEtODEwZi00YzVkMzUyNDFlNjk",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZTU18xYjcyOGZmOS03ZGU4LTRjYjctOTU0MC0yOTMyMGI1YTQyY2I",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZNU185ZWNhNzgxNC0zMzEzLTQ2NGYtOTY0Mi0wMjM5ODc1YmM5Zjg",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZUQ19hMjQ3MzgyOC1hOTgwLTQ3MmYtODE5ZC02YjljY2UwOGU5MmI"
              ],
              "created": "2026-09-21T08:45:41.526Z",
              "lastModified": "2026-09-21T08:45:53.137Z",
              "status": "unknown",
              "invitePending": true,
              "loginEnabled": true,
              "type": "person",
              "siteUrls": [
                "webexone-ai-assistant-sbx.webex.com"
              ]
            },
            {
              "id": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS9hMjQ2YjQ4Yi01NGVjLTQxMGQtYTVhMC00MGNiNjQyM2E1ZWY",
              "emails": [
                "pod11@webexone-ai-assistant.wbx.ai"
              ],
              "sipAddresses": [
                {
                  "type": "cloud-calling",
                  "value": "pod11@webexone-ai-assistant-sbx.calls.webex.com",
                  "primary": true
                }
              ],
              "displayName": "Pod 11",
              "nickName": "Pod",
              "firstName": "Pod",
              "lastName": "11",
              "orgId": "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi83NDk4M2ZkNS01YzE4LTQ1Y2ItYmZjZC01MDcwMDVlMDViMGY",
              "roles": [
                "Y2lzY29zcGFyazovL3VzL1JPTEUvaWRfZnVsbF9hZG1pbg"
              ],
              "licenses": [
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZUTV9mNWZkZTM1Zi00NzA0LTQ2MGEtODEwZi00YzVkMzUyNDFlNjk",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZTU18xYjcyOGZmOS03ZGU4LTRjYjctOTU0MC0yOTMyMGI1YTQyY2I",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZNU185ZWNhNzgxNC0zMzEzLTQ2NGYtOTY0Mi0wMjM5ODc1YmM5Zjg",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZUQ19hMjQ3MzgyOC1hOTgwLTQ3MmYtODE5ZC02YjljY2UwOGU5MmI"
              ],
              "created": "2026-09-21T08:46:08.286Z",
              "lastModified": "2026-09-21T08:46:19.901Z",
              "status": "unknown",
              "invitePending": true,
              "loginEnabled": true,
              "type": "person",
              "siteUrls": [
                "webexone-ai-assistant-sbx.webex.com"
              ]
            },
            {
              "id": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS82MjAwMjBmZC1jMTczLTQyZmUtYWYxMS05NGM3NzYyNzY2NDA",
              "emails": [
                "pod12@webexone-ai-assistant.wbx.ai"
              ],
              "sipAddresses": [
                {
                  "type": "cloud-calling",
                  "value": "pod12@webexone-ai-assistant-sbx.calls.webex.com",
                  "primary": true
                }
              ],
              "displayName": "Pod 12",
              "nickName": "Pod",
              "firstName": "Pod",
              "lastName": "12",
              "orgId": "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi83NDk4M2ZkNS01YzE4LTQ1Y2ItYmZjZC01MDcwMDVlMDViMGY",
              "roles": [
                "Y2lzY29zcGFyazovL3VzL1JPTEUvaWRfZnVsbF9hZG1pbg"
              ],
              "licenses": [
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZUTV9mNWZkZTM1Zi00NzA0LTQ2MGEtODEwZi00YzVkMzUyNDFlNjk",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZTU18xYjcyOGZmOS03ZGU4LTRjYjctOTU0MC0yOTMyMGI1YTQyY2I",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZNU185ZWNhNzgxNC0zMzEzLTQ2NGYtOTY0Mi0wMjM5ODc1YmM5Zjg",
                "Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvNzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBmOkZUQ19hMjQ3MzgyOC1hOTgwLTQ3MmYtODE5ZC02YjljY2UwOGU5MmI"
              ],
              "created": "2026-09-21T08:46:13.957Z",
              "lastModified": "2026-09-21T08:46:25.563Z",
              "status": "unknown",
              "invitePending": true,
              "loginEnabled": true,
              "type": "person",
              "siteUrls": [
                "webexone-ai-assistant-sbx.webex.com"
              ]
            }
          ]
        }
        ```

## Step 3.4 - Webex APIs for Troubleshooting

You now know how to call Webex APIs with different methdos (cURL, Bruno, and Python). The rest of this section uses that on the APIs an administrator actually reaches for when something is wrong: platform status, audit events, reports, call history, and meeting quality.

These are organization-level calls. The official MCP servers you used before act on *a person's* meetings and messages. They do not cover Webex Calling or Control Hub troubleshooting, which is the gap we will fill.

!!! Warning "Important"
    Your organization also need **[Pro Pack for Control Hub](https://help.webex.com/en-us/article/np3c1rm/Pro-Pack-For-Control-Hub){:target="_blank"}**. That add-on is mandatory for different APIs. Without it, sign-in history, long-range reports, and deep compliance lookback are limited or blocked.

    Pro-pack is already enabled on this sandbox.

From here on we work in Bruno, adding each call to your `WebexOne` collection so you can keep the requests and reuse the IDs they return.

Unless a call says otherwise, every request needs the same header:

| Header | Value |
| --- | --- |
| `Authorization` | `Bearer {{token}}` |

!!! Warning "Important"
    The organization ID has already been set for you, both below and as `WEBEX_ORG_ID` in `.env`: `74983fd5-5c18-45cb-bfcd-507005e05b0f`.

    Add it to your Bruno environment as `orgId` so you can write `{{orgId}}` instead of pasting it:

    ![Bruno](./assets/bruno_13.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    Save it.    

### Webex Status API

Check platform health before deep-diving into org-specific issues.

Reference: [Webex Status API](https://developer.webex.com/calling/docs/webex-status-api){:target="_blank"}

This is the one exception to the rule above: the Status API is public, so these two requests need **no** `Authorization` header at all.

1. Create a `GET` request called `Webex Status` with the URL `https://status.webex.com/status.json` and **Send**:

    ![Bruno](./assets/bruno_14.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    `Yellow` indicates that there is an incident going on.

2. Create a `GET` request called `Unresolved Incidents` with the URL `https://status.webex.com/unresolved-incidents.json` and **Send**:

    ![Bruno](./assets/bruno_15.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    ??? Note "Full response"
        ```json
        {
          "incidents": [
            {
              "sourceId": null,
              "end_at": "2026-09-14T20:45:36.847Z",
              "commercial": true,
              "components": [
                {
                  "commercial": true,
                  "link": null,
                  "created_at": "2023-02-13T14:17:51.680Z",
                  "description": null,
                  "externalId": null,
                  "fedRAMP": false,
                  "helpLink": null,
                  "updated_at": "2026-03-04T17:34:57.306Z",
                  "group_id": null,
                  "unavailableRegions": [],
                  "name": "Gateway and Solutions",
                  "regionStatusMap": null,
                  "id": "334c1400aba911ed93ed5f2993f8c502",
                  "position": 3,
                  "isGroup": "Y",
                  "product_group": "WebexMeeting",
                  "serviceId": "891",
                  "status": "operational"
                }
              ],
              "autoStatusSetting": false,
              "regions": [
                "N. America (West)",
                "N. America (East)"
              ],
              "incidentType": "INCIDENT",
              "created_at": "2026-09-14T20:45:36.847Z",
              "changeId": null,
              "start_at": "2026-09-14T20:45:36.847Z",
              "degradedComponents": [
                "334c1400aba911ed93ed5f2993f8c502",
                "fac6cf70e2b311edafb4e799ce19309d"
              ],
              "majorComponents": [],
              "updated_at": "2026-09-22T21:05:13.399Z",
              "id": "3d2595f0b07d11f1b8d75d44686f2b97",
              "serviceId": "891",
              "autoStatusSettingFlag": null,
              "impact": "minor",
              "forceRestoreComponentsFlag": null,
              "externalId": null,
              "forceRestoreComponents": false,
              "fedRAMP": false,
              "commercialFlag": null,
              "maintenanceComponents": [],
              "fedRAMPFlag": null,
              "resolved_at": null,
              "name": "Gateway and Solutions: Some users may experience intermittent degraded audio/video quality when joining Microsoft Teams meetings via VIMT",
              "incident_updates": [
                {
                  "incident_id": "3d2595f0b07d11f1b8d75d44686f2b97",
                  "updated_at": "2026-09-22T21:05:13.395Z",
                  "created_at": "2026-09-22T21:05:13.395Z",
                  "externalId": null,
                  "message_id": "4dba9030b6c911f18e937fbe2e0dc78e",
                  "body": "Our engineering team continues to actively work with the vendor to address an issue affecting users joining Microsoft Teams meetings via VIMT. We are continuing to validate service stability before fully restoring traffic routing for the region. During this period, users may experience increased latency or a degraded meeting experience.\n\nWe are monitoring the situation closely and will provide a follow-up update within 24 hours, or sooner if there is significant progress.",
                  "status": "monitoring"
                },
                {
                  "incident_id": "3d2595f0b07d11f1b8d75d44686f2b97",
                  "updated_at": "2026-09-21T20:44:59.631Z",
                  "created_at": "2026-09-21T20:44:59.631Z",
                  "externalId": null,
                  "message_id": "4fdb1ff0b5fd11f1bf47f3e2c2e736de",
                  "body": "Our engineering team continues to actively work with the vendor to address an issue affecting users joining Microsoft Teams meetings via VIMT. We are continuing to validate service stability before fully restoring traffic routing for the region. During this period, users may experience increased latency or a degraded meeting experience.\n\nWe are monitoring the situation closely and will provide a follow-up update within 24 hours, or sooner if there is significant progress.",
                  "status": "monitoring"
                },
                {
                  "incident_id": "3d2595f0b07d11f1b8d75d44686f2b97",
                  "updated_at": "2026-09-20T20:29:26.487Z",
                  "created_at": "2026-09-20T20:29:26.487Z",
                  "externalId": null,
                  "message_id": "f93ee670b53111f1834c5317e7c1d52e",
                  "body": "Our engineering team continues to actively work with the vendor to address an issue affecting users joining Microsoft Teams meetings via VIMT. We are continuing to validate service stability before fully restoring traffic routing for the region. During this period, users may experience increased latency or a degraded meeting experience.\n\nWe are monitoring the situation closely and will provide a follow-up update within 24 hours, or sooner if there is significant progress.",
                  "status": "monitoring"
                },
                {
                  "incident_id": "3d2595f0b07d11f1b8d75d44686f2b97",
                  "updated_at": "2026-09-19T20:35:30.813Z",
                  "created_at": "2026-09-19T20:35:30.813Z",
                  "externalId": null,
                  "message_id": "a7fce2d0b46911f1b8d75d44686f2b97",
                  "body": "Our engineering team continues to actively work with the vendor to address an issue affecting users joining Microsoft Teams meetings via VIMT. We are continuing to validate service stability before fully restoring traffic routing for the region. During this period, users may experience increased latency or a degraded meeting experience.\n\nWe are monitoring the situation closely and will provide a follow-up update within 24 hours, or sooner if there is significant progress.",
                  "status": "monitoring"
                },
                {
                  "incident_id": "3d2595f0b07d11f1b8d75d44686f2b97",
                  "updated_at": "2026-09-18T20:15:06.000Z",
                  "created_at": "2026-09-18T20:15:06.000Z",
                  "externalId": null,
                  "message_id": "a3878100b39d11f19c3993046b985b88",
                  "body": "Our engineering team is actively working with the vendor to address an issue affecting users joining Microsoft Teams meetings via VIMT. We are currently validating service stability before fully restoring traffic routing for the region. During this period, users may experience increased latency or a degraded meeting experience.\n\nWe are monitoring the situation closely and will provide a follow-up update within 24 hours, or sooner if there is significant progress.",
                  "status": "monitoring"
                },
                {
                  "incident_id": "3d2595f0b07d11f1b8d75d44686f2b97",
                  "updated_at": "2026-09-17T20:22:33.282Z",
                  "created_at": "2026-09-17T20:22:33.282Z",
                  "externalId": null,
                  "message_id": "83b79220b2d511f1834c5317e7c1d52e",
                  "body": "Engineering continues to monitor the issue affecting some users joining Microsoft Teams meetings via VIMT.\n\nCisco teams are working with the vendor toward full resolution and are validating service stability before restoring normal traffic routing for the affected region. During this time, some users may experience increased latency or a reduced meeting experience.\n\nWe will provide the next update within 24 hours, or sooner if there is a significant change in status.\n\nThank you for your patience while we work to address this service incident.",
                  "status": "monitoring"
                },
                {
                  "incident_id": "3d2595f0b07d11f1b8d75d44686f2b97",
                  "updated_at": "2026-09-16T20:17:21.334Z",
                  "created_at": "2026-09-16T20:17:21.334Z",
                  "externalId": null,
                  "message_id": "9f5e5560b20b11f1b8d75d44686f2b97",
                  "body": "Engineering continues to monitor the issue affecting some users joining Microsoft Teams meetings via VIMT.\n \nThe vendor continues to work on mitigation, and Cisco teams are performing controlled validation before restoring normal traffic routing for the affected region. During this validation period, traffic may continue to route through alternate regions, which can result in increased latency or a reduced meeting experience for some users.\n \nWe will provide the next update within 24 hours, or sooner if there is a significant change in status.\n \nThank you for your patience while we work to address this service incident.",
                  "status": "monitoring"
                },
                {
                  "incident_id": "3d2595f0b07d11f1b8d75d44686f2b97",
                  "updated_at": "2026-09-15T20:21:30.936Z",
                  "created_at": "2026-09-15T20:21:30.936Z",
                  "externalId": null,
                  "message_id": "09bad380b14311f1be3dcb367ccf780a",
                  "body": "Engineering continues to monitor the issue causing some users joining Microsoft Teams meetings via VIMT to experience intermittent degraded audio or video quality.\n \nOur teams remain actively engaged with the vendor on the underlying network issue. A vendor-side mitigation is still in progress, and Cisco teams are continuing to monitor traffic routing and service performance while we await confirmation that the issue has been fully resolved.\n \nUntil resolution is confirmed and validated, customers may continue to experience intermittent media quality degradation and regional call routing changes during peak usage periods.\n \nWe will provide the next update within 24 hours, or sooner if there is a significant change in status.\n \nThank you for your patience while we work to address this service incident.",
                  "status": "monitoring"
                },
                {
                  "incident_id": "3d2595f0b07d11f1b8d75d44686f2b97",
                  "updated_at": "2026-09-14T20:45:36.884Z",
                  "affect_components": [
                    {
                      "componentId": "fac6cf70e2b311edafb4e799ce19309d",
                      "deleted": false,
                      "discription": null,
                      "lastModifiedTime": null,
                      "createTime": "2026-09-14T20:45:36.905Z",
                      "currentStatus": "degraded_performance",
                      "affectId": "3d2e4880b07d11f1b8d75d44686f2b97",
                      "messageId": "3d2b3b40b07d11f1b8d75d44686f2b97",
                      "componentName": " Video Integration for Microsoft Teams (VIMT) ",
                      "region": "N. America (East)",
                      "status": "degraded_performance"
                    },
                    {
                      "componentId": "fac6cf70e2b311edafb4e799ce19309d",
                      "deleted": false,
                      "discription": null,
                      "lastModifiedTime": null,
                      "createTime": "2026-09-14T20:45:36.904Z",
                      "currentStatus": "degraded_performance",
                      "affectId": "3d2e2170b07d11f1b8d75d44686f2b97",
                      "messageId": "3d2b3b40b07d11f1b8d75d44686f2b97",
                      "componentName": " Video Integration for Microsoft Teams (VIMT) ",
                      "region": "N. America (West)",
                      "status": "degraded_performance"
                    },
                    {
                      "componentId": "334c1400aba911ed93ed5f2993f8c502",
                      "deleted": false,
                      "discription": null,
                      "lastModifiedTime": null,
                      "createTime": "2026-09-14T20:45:36.903Z",
                      "currentStatus": "degraded_performance",
                      "affectId": "3d2dfa60b07d11f1b8d75d44686f2b97",
                      "messageId": "3d2b3b40b07d11f1b8d75d44686f2b97",
                      "componentName": "Gateway and Solutions",
                      "region": "N. America (West)",
                      "status": "degraded_performance"
                    },
                    {
                      "componentId": "334c1400aba911ed93ed5f2993f8c502",
                      "deleted": false,
                      "discription": null,
                      "lastModifiedTime": null,
                      "createTime": "2026-09-14T20:45:36.901Z",
                      "currentStatus": "degraded_performance",
                      "affectId": "3d2c73c0b07d11f1b8d75d44686f2b97",
                      "messageId": "3d2b3b40b07d11f1b8d75d44686f2b97",
                      "componentName": "Gateway and Solutions",
                      "region": "N. America (East)",
                      "status": "degraded_performance"
                    }
                  ],
                  "created_at": "2026-09-14T20:45:36.884Z",
                  "externalId": null,
                  "message_id": "3d2b3b40b07d11f1b8d75d44686f2b97",
                  "body": "Engineering is monitoring an issue that may impact some users joining Microsoft Teams meetings via VIMT. Users may experience intermittent degraded audio or video quality, and in some cases, calls may be routed through alternate regions, which can result in increased latency or a reduced meeting experience.\n\nOur teams are actively working with the vendor to investigate and resolve the underlying network issue. Until the vendor provides confirmation of resolution, customers may continue to experience intermittent media quality degradation and regional call routing changes during peak usage periods.\n\nWe will provide the next update within 24 hours, or sooner if there is a significant change in status.\n\nThank you for your patience while we work to address this service incident.",
                  "status": "monitoring"
                }
              ],
              "locations": null,
              "publicationId": "PUB0016437",
              "incidentNumber": "INC0056900",
              "status": "monitoring"
            }
          ]
        }    
        ```

### Audit and compliance

When something changes in the organization, Webex keeps a record. There are three APIs for that, and they are not interchangeable: each one answers a different "who did what", and each one needs a different kind of administrator.

| API | What it records | Who can call it in this lab |
| --- | --- | --- |
| [Admin Audit Events](https://developer.webex.com/admin/docs/api/v1/admin-audit-events){:target="_blank"} | Control Hub configuration changes | Full admin |
| [Security Audit Events](https://developer.webex.com/admin/docs/api/v1/security-audit-events){:target="_blank"} | User sign-in and sign-out | Full admin |
| [Compliance Events](https://developer.webex.com/compliance/docs/api/v1/events){:target="_blank"} | Messages, files, and space membership | **Compliance Officer** |

In this lab, we will be using the Admin Audit Events API.

#### Admin Audit Events

Admin Audit Events will not accept a bare URL: `orgId`, `from`, and `to` are all mandatory.

1. Create a `GET` request called `Admin Audit Events` with the URL `https://webexapis.com/v1/adminAudit/events`.
2. In the **Params** tab, add and click **Send**:

    | Parameter | Value |
    | --- | --- |
    | `orgId` | `{{orgId}}` |
    | `from` | `2026-19-15T00:00:00.000Z` |
    | `to` | `2026-09-23T23:59:59.000Z` |
    | `max` | `10` |

    ![Bruno](./assets/bruno_16.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    The useful values sit inside each item's `data` object. To filter, you can add `eventCategories` parameter in your query.

    ??? Note "Full response"
        ```json
        {
          "items": [
            {
              "data": {
                "actorOrgName": "Troubleshoot and manage your organization with an AI assistant",
                "isInternal": null,
                "targetName": "Events",
                "configData": null,
                "eventDescription": "Service App authorization is changed by an admin",
                "actorName": "Pod 0",
                "actorEmail": "pod0@webexone-ai-assistant.wbx.ai",
                "configType": null,
                "trackingId": "ATLAS_0519fd38-acad-475d-b60a-137d397fbd8e_4",
                "serviceAppScopes": [
                  "spark:kms",
                  "audit:events_read"
                ],
                "serviceAppSites": [
                  "No sites configured"
                ],
                "configOperationType": null,
                "targetType": "INTEGRATION",
                "targetId": "Y2lzY29zcGFyazovL3VzL0FQUExJQ0FUSU9OL0M5MGZhYjUzYTdhOGMwZGZhZWY1OTViZGIwNjI3YzdlNzAwYmI1NTI4NjY0YTVhYWMxMmM3YTYwYjIwNDNiMjg4",
                "actorUserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
                "eventCategory": "INTEGRATION",
                "displayName": null,
                "actorIp": "173.38.220.36",
                "targetOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "authorizedStatus": "AUTHORIZED",
                "actionText": "The admin Pod 0 with email pod0@webexone-ai-assistant.wbx.ai AUTHORIZED the Service App Events: Y2lzY29zcGFyazovL3VzL0FQUExJQ0FUSU9OL0M5MGZhYjUzYTdhOGMwZGZhZWY1OTViZGIwNjI3YzdlNzAwYmI1NTI4NjY0YTVhYWMxMmM3YTYwYjIwNDNiMjg4 with the scopes [spark:kms, audit:events_read] and sites [No sites configured] on 2026-09-23T13:03:31.431675854Z[UTC]",
                "configId": null,
                "targetOrgName": "Troubleshoot and manage your organization with an AI assistant"
              },
              "created": "2026-09-23T13:03:31.431Z",
              "actorOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
              "id": "MjEzOWM1YTItMzE4ZS00MjllLWJhZGMtYWMxNWRjYTdhM2Zh",
              "actorId": "MThjMmM0ODktMmZlZi00YTE1LWE0YmQtY2FiN2I2NWQ4NDE2"
            },
            {
              "data": {
                "actorOrgName": "Troubleshoot and manage your organization with an AI assistant",
                "isInternal": null,
                "targetName": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "configData": null,
                "actorManagementRealm": null,
                "eventDescription": "An Admin logged in",
                "actorName": "Pod 0",
                "actorEmail": "pod0@webexone-ai-assistant.wbx.ai",
                "targetManagementRealm": null,
                "adminRoles": [
                  "User",
                  "Full_Admin",
                  "id_full_admin"
                ],
                "configType": null,
                "trackingId": "ATLAS_fdfcb73e-2be4-4b93-b7f3-76c73e4799ff_4",
                "configOperationType": null,
                "targetType": "ORG",
                "targetId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "actorUserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
                "eventCategory": "LOGINS",
                "displayName": null,
                "targetTenantUid": null,
                "actorIp": "173.38.220.36",
                "targetOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "targetTenantName": null,
                "actionText": "Pod 0 logged into organization 74983fd5-5c18-45cb-bfcd-507005e05b0f.",
                "actorTenantUid": null,
                "actorTenantName": null,
                "configId": null,
                "targetOrgName": "Troubleshoot and manage your organization with an AI assistant"
              },
              "created": "2026-09-23T12:13:50.759Z",
              "actorOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
              "id": "ZDUyMTI3NjgtYzRjYy00NDM0LWJhNDItYzZkNjE1ZmM1Njli",
              "actorId": "MThjMmM0ODktMmZlZi00YTE1LWE0YmQtY2FiN2I2NWQ4NDE2"
            },
            {
              "data": {
                "isInternal": null,
                "configData": null,
                "actorName": "pod0@webexone-ai-assistant.wbx.ai",
                "targetManagementRealm": null,
                "configType": null,
                "eventStatus": "SUCCESS",
                "configOperationType": null,
                "actorUserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
                "displayName": null,
                "actionClientId": "C80fb9c7096bd8474627317ee1d7a817eff372ca9c9cee3ce43c3ea3e8d1511ec",
                "actorIp": "2001:420:4919:1300:51fd:d522:b958:88df",
                "targetOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "actorTenantUid": null,
                "configId": null,
                "actorOrgName": "Troubleshoot and manage your organization with an AI assistant",
                "targetName": "Troubleshoot and manage your organization with an AI assistant",
                "actorManagementRealm": null,
                "eventDescription": "User Logout Attempted",
                "actorEmail": "pod0@webexone-ai-assistant.wbx.ai",
                "trackingId": "ATLAS_57caf018-4a70-4a5f-93ff-34591fc83d9b_162",
                "actionClientName": "Webex Admin Portal",
                "targetType": "PERSON",
                "targetId": "MThjMmM0ODktMmZlZi00YTE1LWE0YmQtY2FiN2I2NWQ4NDE2",
                "eventCategory": "LOGOUT",
                "targetTenantUid": null,
                "targetTenantName": null,
                "actionText": "pod0@webexone-ai-assistant.wbx.ai attempted to log out from Webex Admin Portal. Logout status: SUCCESS.  ",
                "actorTenantName": null,
                "targetOrgName": "Troubleshoot and manage your organization with an AI assistant",
                "failedReason": " "
              },
              "actorOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
              "actorId": "MThjMmM0ODktMmZlZi00YTE1LWE0YmQtY2FiN2I2NWQ4NDE2",
              "created": "2026-09-23T12:13:31.229Z",
              "id": "Mjc2NmRiMDAtNzk4ZS00MTQ3LWFmZDgtNWNlYWQ3YzVhNmJh"
            },
            {
              "data": {
                "isInternal": null,
                "configData": null,
                "operationType": "CREATE",
                "actorName": "Pod 0",
                "targetManagementRealm": null,
                "configType": null,
                "configOperationType": null,
                "actorUserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
                "displayName": null,
                "actorIp": "2001:420:4919:1300:51fd:d522:b958:88df",
                "targetOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "actorTenantUid": null,
                "configId": null,
                "actorOrgName": "Troubleshoot and manage your organization with an AI assistant",
                "targetName": "Troubleshoot and manage your organization with an AI assistant",
                "actorManagementRealm": null,
                "eventDescription": "An org setting was created or updated.",
                "actorEmail": "pod0@webexone-ai-assistant.wbx.ai",
                "settingKey": "sign-in-audit",
                "settingName": "Sign In Audit Setting",
                "settingValue": "true",
                "trackingId": "ATLAS_57caf018-4a70-4a5f-93ff-34591fc83d9b_158",
                "previousValue": "Null",
                "targetType": "ORG",
                "targetId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "eventCategory": "ORG_SETTINGS",
                "targetTenantUid": null,
                "targetTenantName": null,
                "actionText": "Pod 0 has modified the value of setting Sign In Audit Setting for ORG \"Troubleshoot and manage your organization with an AI assistant\". New value = true, Previous value = Null.",
                "entityType": "ORG",
                "actorTenantName": null,
                "targetOrgName": "Troubleshoot and manage your organization with an AI assistant"
              },
              "actorOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
              "actorId": "MThjMmM0ODktMmZlZi00YTE1LWE0YmQtY2FiN2I2NWQ4NDE2",
              "created": "2026-09-23T12:09:39.867Z",
              "id": "ODQ0ZGQ5ZTQtMmEyZi00YzU1LWFhZDktMzFhNzJhMzY3ZWI5"
            },
            {
              "data": {
                "actorOrgName": "Troubleshoot and manage your organization with an AI assistant",
                "isInternal": null,
                "targetName": "Using Admin Name: Pod 0",
                "configData": null,
                "eventDescription": "User's token was revoked by an Admin.",
                "actorName": "Pod 0",
                "actorEmail": "pod0@webexone-ai-assistant.wbx.ai",
                "clientId": "No Client Id",
                "tokenId": "Y2lzY29zcGFyazovL3VybjpURUFNOnVzLXdlc3QtMl9yL0FVVEhPUklaQVRJT04vYTZlNzk3MDUtNzg2My00MTZjLWE0ZDYtY2U5Y2E1NzE0Yzkz",
                "configType": null,
                "trackingId": "ROUTERGW_9563aade-8852-48d7-ad01-9d168ebe5077_0",
                "configOperationType": null,
                "targetType": "PERSON",
                "targetId": "Using Admin Id: 18c2c489-2fef-4a15-a4bd-cab7b65d8416",
                "actorUserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
                "eventCategory": "USERS",
                "displayName": null,
                "actorIp": "170.72.250.110",
                "targetOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "actionText": "Pod 0 revoked Using Admin Id: 18c2c489-2fef-4a15-a4bd-cab7b65d8416's Y2lzY29zcGFyazovL3VybjpURUFNOnVzLXdlc3QtMl9yL0FVVEhPUklaQVRJT04vYTZlNzk3MDUtNzg2My00MTZjLWE0ZDYtY2U5Y2E1NzE0Yzkz token belonging to 74983fd5-5c18-45cb-bfcd-507005e05b0f org with client_id No Client Id",
                "configId": null,
                "targetOrgName": "Troubleshoot and manage your organization with an AI assistant"
              },
              "created": "2026-09-23T11:51:09.026Z",
              "actorOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
              "id": "OTMzNmFhZWEtMDMwYi00MWUxLTg5MDEtMmYwYTljMGRiZDhh",
              "actorId": "MThjMmM0ODktMmZlZi00YTE1LWE0YmQtY2FiN2I2NWQ4NDE2"
            },
            {
              "data": {
                "isInternal": null,
                "configData": null,
                "actorName": "Pod 0",
                "targetManagementRealm": "collab",
                "changedAttributes": [
                  "userPreferences"
                ],
                "configType": null,
                "configOperationType": null,
                "actorUserAgent": "NoUserAgentAvailableBot/0.1 (+http://www.cisco.com)",
                "displayName": null,
                "actorClientId": "C80fb9c7096bd8474627317ee1d7a817eff372ca9c9cee3ce43c3ea3e8d1511ec",
                "actorIp": "2001:420:4919:1300:51fd:d522:b958:88df",
                "targetOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "actorTenantUid": null,
                "configId": null,
                "actorOrgName": "Troubleshoot and manage your organization with an AI assistant",
                "targetName": "Pod 0",
                "actorManagementRealm": null,
                "changeDetailId": "297079186",
                "eventDescription": "User was updated",
                "actorEmail": "pod0@webexone-ai-assistant.wbx.ai",
                "trackingId": "ATLAS_359f8596-582f-49ec-8735-55351dbd6265_41",
                "targetType": "PERSON",
                "targetId": "MThjMmM0ODktMmZlZi00YTE1LWE0YmQtY2FiN2I2NWQ4NDE2",
                "eventCategory": "WEBEX_IDENTITY",
                "targetTenantUid": null,
                "targetTenantName": null,
                "actorClientName": "Webex Admin Portal",
                "actionText": "Pod 0 changed user Pod 0, the changed attributes are [userPreferences]. The change source is Webex Admin Portal. The change detail ID 297079186.",
                "actorTenantName": null,
                "targetOrgName": "Troubleshoot and manage your organization with an AI assistant"
              },
              "actorOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
              "actorId": "MThjMmM0ODktMmZlZi00YTE1LWE0YmQtY2FiN2I2NWQ4NDE2",
              "created": "2026-09-23T11:48:10.200Z",
              "id": "NjU5OTRhZTItMDIxNC00NTYyLWFkZWQtOTM1ZmQzN2Q3YTgy"
            },
            {
              "data": {
                "isInternal": null,
                "configData": null,
                "operationType": "CREATE",
                "actorName": "Pod 0",
                "targetManagementRealm": null,
                "configType": null,
                "configOperationType": null,
                "actorUserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
                "displayName": null,
                "actorIp": "2001:420:4919:1300:51fd:d522:b958:88df",
                "targetOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "actorTenantUid": null,
                "configId": null,
                "actorOrgName": "Troubleshoot and manage your organization with an AI assistant",
                "targetName": "Pod 0",
                "actorManagementRealm": null,
                "eventDescription": "An org setting was created or updated.",
                "actorEmail": "pod0@webexone-ai-assistant.wbx.ai",
                "settingKey": "terms-of-service-user-info",
                "settingName": "terms-of-service-user-info",
                "settingValue": "{\"acceptedDateTimestamp\":\"2026-09-23 13\\u003A48\\u003A07\",\"tosVersion\":\"0.0.0\"}",
                "trackingId": "ATLAS_359f8596-582f-49ec-8735-55351dbd6265_40",
                "previousValue": "Null",
                "targetType": "PERSON",
                "targetId": "MThjMmM0ODktMmZlZi00YTE1LWE0YmQtY2FiN2I2NWQ4NDE2",
                "eventCategory": "ORG_SETTINGS",
                "targetTenantUid": null,
                "targetTenantName": null,
                "actionText": "Pod 0 has modified the value of setting terms-of-service-user-info for USER \"Pod 0\". New value = {\"acceptedDateTimestamp\":\"2026-09-23 13\\u003A48\\u003A07\",\"tosVersion\":\"0.0.0\"}, Previous value = Null.",
                "entityType": "USER",
                "actorTenantName": null,
                "targetOrgName": "Troubleshoot and manage your organization with an AI assistant"
              },
              "actorOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
              "actorId": "MThjMmM0ODktMmZlZi00YTE1LWE0YmQtY2FiN2I2NWQ4NDE2",
              "created": "2026-09-23T11:48:08.319Z",
              "id": "MTBhNzEzYTYtYzAzZS00NzU1LWI1NDMtZWJiYjI3NDdiOGVh"
            },
            {
              "data": {
                "actorOrgName": "Troubleshoot and manage your organization with an AI assistant",
                "isInternal": null,
                "targetName": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "configData": null,
                "actorManagementRealm": null,
                "eventDescription": "An Admin logged in",
                "actorName": "Pod 0",
                "actorEmail": "pod0@webexone-ai-assistant.wbx.ai",
                "targetManagementRealm": null,
                "adminRoles": [
                  "User",
                  "Full_Admin",
                  "id_full_admin"
                ],
                "configType": null,
                "trackingId": "ATLAS_d84eac32-24b4-42c7-87b1-6650e775e47a_4",
                "configOperationType": null,
                "targetType": "ORG",
                "targetId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "actorUserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
                "eventCategory": "LOGINS",
                "displayName": null,
                "targetTenantUid": null,
                "actorIp": "2001:420:4919:1300:51fd:d522:b958:88df",
                "targetOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "targetTenantName": null,
                "actionText": "Pod 0 logged into organization 74983fd5-5c18-45cb-bfcd-507005e05b0f.",
                "actorTenantUid": null,
                "actorTenantName": null,
                "configId": null,
                "targetOrgName": "Troubleshoot and manage your organization with an AI assistant"
              },
              "created": "2026-09-23T11:47:58.533Z",
              "actorOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
              "id": "ZGYwMjBiYWYtM2I1YS00MjFlLWJmMDQtYThhZDUxMWMwZmNl",
              "actorId": "MThjMmM0ODktMmZlZi00YTE1LWE0YmQtY2FiN2I2NWQ4NDE2"
            },
            {
              "data": {
                "isInternal": null,
                "configData": null,
                "actorName": "admin@webexone-ai-assistant.wbx.ai",
                "targetManagementRealm": null,
                "configType": null,
                "eventStatus": "SUCCESS",
                "configOperationType": null,
                "actorUserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
                "displayName": null,
                "actionClientId": "C80fb9c7096bd8474627317ee1d7a817eff372ca9c9cee3ce43c3ea3e8d1511ec",
                "actorIp": "2001:420:4919:1300:51fd:d522:b958:88df",
                "targetOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "actorTenantUid": null,
                "configId": null,
                "actorOrgName": "Troubleshoot and manage your organization with an AI assistant",
                "targetName": "Troubleshoot and manage your organization with an AI assistant",
                "actorManagementRealm": null,
                "eventDescription": "User Logout Attempted",
                "actorEmail": "admin@webexone-ai-assistant.wbx.ai",
                "trackingId": "ATLAS_f5125c82-7523-4352-b066-148d77a04797_99",
                "actionClientName": "Webex Admin Portal",
                "targetType": "PERSON",
                "targetId": "ZTZhMzBjMjYtYTUwZi00MTgwLTgzODEtMjQyMmRjYTlmMDI3",
                "eventCategory": "LOGOUT",
                "targetTenantUid": null,
                "targetTenantName": null,
                "actionText": "admin@webexone-ai-assistant.wbx.ai attempted to log out from Webex Admin Portal. Logout status: SUCCESS.  ",
                "actorTenantName": null,
                "targetOrgName": "Troubleshoot and manage your organization with an AI assistant",
                "failedReason": " "
              },
              "actorOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
              "actorId": "ZTZhMzBjMjYtYTUwZi00MTgwLTgzODEtMjQyMmRjYTlmMDI3",
              "created": "2026-09-23T11:47:16.732Z",
              "id": "YmE4NzdhZmEtMTU5OC00OTkxLTkxMDctYTgwYWY0MzNhOTNj"
            },
            {
              "data": {
                "actorOrgName": "Troubleshoot and manage your organization with an AI assistant",
                "isInternal": null,
                "targetName": "Using Admin Name: Pod 40",
                "configData": null,
                "eventDescription": "User's token was revoked by an Admin.",
                "actorName": "Pod 40",
                "actorEmail": "pod40@webexone-ai-assistant.wbx.ai",
                "clientId": "No Client Id",
                "tokenId": "Y2lzY29zcGFyazovL3VybjpURUFNOnVzLXdlc3QtMl9yL0FVVEhPUklaQVRJT04vZjc3YmI4YjEtOGIxMi00ODc3LWEzYTItOTE2NjQwZDcyZTlj",
                "configType": null,
                "trackingId": "ROUTERGW_957ca3f2-7417-4be5-82f7-7dd64d500b2c_0",
                "configOperationType": null,
                "targetType": "PERSON",
                "targetId": "Using Admin Id: e2ad5d62-8879-4d7c-8a9c-17733f4db1e4",
                "actorUserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
                "eventCategory": "USERS",
                "displayName": null,
                "actorIp": "170.72.250.167",
                "targetOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
                "actionText": "Pod 40 revoked Using Admin Id: e2ad5d62-8879-4d7c-8a9c-17733f4db1e4's Y2lzY29zcGFyazovL3VybjpURUFNOnVzLXdlc3QtMl9yL0FVVEhPUklaQVRJT04vZjc3YmI4YjEtOGIxMi00ODc3LWEzYTItOTE2NjQwZDcyZTlj token belonging to 74983fd5-5c18-45cb-bfcd-507005e05b0f org with client_id No Client Id",
                "configId": null,
                "targetOrgName": "Troubleshoot and manage your organization with an AI assistant"
              },
              "created": "2026-09-23T10:08:50.656Z",
              "actorOrgId": "NzQ5ODNmZDUtNWMxOC00NWNiLWJmY2QtNTA3MDA1ZTA1YjBm",
              "id": "MmNhZTdlNTUtNDcyYi00OWU1LWEwYTUtOGRiZmZiOGE2ZmI0",
              "actorId": "ZTJhZDVkNjItODg3OS00ZDdjLThhOWMtMTc3MzNmNGRiMWU0"
            }
          ]
        }
        ```

#### Security Audit Events

This API records who signed in and who signed out **as a user**.

!!! Warning
    Control Hub needs to have **Allow user authentication data** turned on. That toggle lives under **Organization settings** > **Security**, and the API returns nothing until it is on. See [Log and analyze user sign-ins and sign-outs](https://help.webex.com/article/pf66vg){:target="_blank"}:

    ![Control Hub](./assets/controlhub_4.png){ width="350" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

This lab does not explore this API.

<!--
1. Create a `GET` request called `Security Audit Events` with the URL `https://webexapis.com/v1/admin/securityAudit/events`.
2. In the **Params** tab, add and click **Send**:

    | Parameter | Value |
    | --- | --- |
    | `orgId` | `{{orgId}}` |
    | `startTime` | `2026-09-15T00:00:00.000Z` |
    | `endTime` | `2026-09-23T23:59:59.000Z` |
    | `max` | `10` |

    ![Bruno](./assets/bruno_xxx.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    The useful values sit inside each item's `data` object. To filter, you can add `eventCategories` parameter in your query.

    ??? Note "Full response"
        ```json
        ```
-->
#### Compliance Events

The compliance API, `GET https://webexapis.com/v1/events` records messages, files, and space membership. It needs a **Compliance officer** role:

![Control Hub](./assets/controlhub_5.png){ width="350" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

This lab does not explore this API.

### Reports

Reports are not generated automatically. You need to create one from **template** (the kind of report), you **create** a job, and Webex generates a file. That job has its own `id`. That value is the `reportId` you need for every later call.

1. Create a `GET` request called `List Report Templates` with the URL `https://webexapis.com/v1/report/templates` and **Send**.

    ![Bruno](./assets/bruno_17.png){ width="750" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    Find *User Activity Summary*. Note two fields on that item: `Id` is `115` (this is the **template** id, not a report yet) and `identifier` is `org` (the report covers the whole organization, so you will not need a meetings site URL).

2. Create a `POST` request called `Create Report` with the URL `https://webexapis.com/v1/reports`. Open the **Body** tab, choose **JSON**, and paste:

    ```json
    {
      "templateId": 115,
      "startDate": "2026-09-10",
      "endDate": "2026-09-19"
    }
    ```

3. **Send**.

    ![Bruno](./assets/bruno_18.png){ width="750" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

4. Copy the `id` from the response into your Bruno environment as `reportId` and **Save**. That is the identifier of **this** generated report.

    ![Bruno](./assets/bruno_19.png){ width="750" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

5. Create a `GET` request called `Get Report` with the URL `https://webexapis.com/v1/reports/{{reportId}}` and **Send**.

    ![Bruno](./assets/bruno_21.png){ width="750" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

6. If report is done, you will get a `downloadURL` that you can use to get the report. You can also download it from Bruno:

    ![Bruno](./assets/bruno_20.png){ width="750" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

You can also list every report you have created through the API with `GET https://webexapis.com/v1/reports`.

### Calling and meetings troubleshooting

When a user reports that a phone call failed or a meeting had poor audio, you need data to investigate. The APIs for this are different from the ones we've used so far: they live on a **different host** (`analytics-calling.webexapis.com` or `analytics.webexapis.com`), and they return deep diagnostic records.

We will look at two of them: **Detailed Call History** for Webex Calling records (CDRs), and **Meeting Qualities** for per-participant meeting diagnostics.

#### Detailed Call History

See [Understanding the Webex Calling CDR APIs](https://developer.webex.com/blog/understanding-the-webex-calling-cdr-apis){:target="_blank"} and [Detailed Call History](https://developer.webex.com/calling/docs/api/v1/reports-detailed-call-history){:target="_blank"}.

!!! Warning "Do not test this one in the Developer Portal"
    The CDR endpoints are **not compatible with the portal's Try It feature**. It fails with *failed to fetch*, which is not an authorization problem. Use Bruno, cURL, or Python.

??? Note "Reference: Webex Calling Detailed Call History API access"
    To get access to this API, you need a specific role assigned to your user. Until now, there was a specific role called **Webex Calling Detailed Call History API access** that you could assign to a user, but this is getting deprecated by the end of the year:

    ![Control Hub](./assets/controlhub_6.png){ width="550" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    Now, you need to create a new custom role. For that, in **Collaboration Control Hub**, go to **Users** > **Admin roles** > **Create new role**. Make sure you add **Webex Calling Detailed Call History API access**:

    ![Control Hub](./assets/controlhub_7.png){ width="950" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    This role has been pre-assigned to you as part of a group:

    ![Control Hub](./assets/controlhub_9.png){ width="350" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

!!! Tip "Live Stream Detailed Call History"

    There is another CDR API intended to be used when a process pulls CDRs continuously into another store:
    
    - [Live Stream Detailed Call History](https://developer.webex.com/calling/docs/api/v1/reports-live-stream-detailed-call-history){:target="_blank"} 
    
    Its `startTime` / `endTime` are when the **record was written**, not when the call started. Records appear about one minute after a call ends, are kept for only **12 hours**, and each request can cover at most **2 hours**.

1. Create a `GET` request called `Detailed Call History` with the URL `https://analytics-calling.webexapis.com/v1/cdr_feed`.
2. In the **Params** tab, add:

    | Parameter | Value |
    | --- | --- |
    | `startTime` | `2026-09-24T05:00:00.000Z` |
    | `endTime` | `2026-09-24T08:30:00.000Z` |
    | `max` | `10` |

    The window cannot be longer than 12 hours and `endTime` must be at least five minutes in the past.

3. **Send**. Each item is one call.

    ![Bruno](./assets/bruno_22.png){ width="750" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}
    
    !!! Note
        If you get `451`, your organization's data lives in another region. The response body names the host to use instead (`analytics-calling-eu`, `-in`, or `-au`). The older host `https://analytics.webexapis.com/v1/cdr_feed` also still answers.

    ??? Note "Example response"
        ```json
        {
          "items": [
            {
              "Answer time": "",
              "Answered": "false",
              "Direction": "TERMINATING",
              "Called line ID": "NA",
              "Call ID": "",
              "Calling line ID": "Agent-80945336",
              "Start time": "2026-09-24T07:49:10.939Z",
              "Call type": "SIP_INBOUND",
              "Client type": "SIP",
              "Client version": "",
              "Correlation ID": "cf30fa26-7c1a-4099-8ada-b8e57acca6ce",
              "International country": "",
              "Device MAC": "",
              "Duration": 0,
              "Inbound trunk": "",
              "Org UUID": "74983fd5-5c18-45cb-bfcd-507005e05b0f",
              "Original reason": "",
              "OS type": "na",
              "Outbound trunk": "",
              "Redirect reason": "",
              "Related reason": "",
              "Report ID": "ea9cd4c2-b4e8-3e0f-b518-b14906a6d01a",
              "Report time": "2026-09-24T07:49:10.941Z",
              "Route group": "",
              "Site main number": "+16693043560",
              "Site timezone": "-420",
              "Sub client type": "",
              "User UUID": "18c2c489-2fef-4a15-a4bd-cab7b65d8416",
              "User type": "User",
              "User": "Pod 0",
              "Called number": "+12542121223",
              "Calling number": "+48123210049",
              "Location": "Site1",
              "Dialed digits": "",
              "Releasing party": "Local",
              "Redirecting number": "",
              "Site UUID": "a0ac79b3-d37c-4cae-8ab0-5d4ec85adde8",
              "Department ID": "",
              "Transfer related call ID": "",
              "Authorization code": "",
              "Model": "",
              "Local SessionID": "",
              "Remote SessionID": "",
              "Call transfer time": "",
              "Local call ID": "29741232:0",
              "Remote call ID": "",
              "Network call ID": "SDen4q701-ef16d7f23c3fb49bcb04e56284058c03-aoh8mj1050",
              "Related call ID": "",
              "User number": "+12542121223",
              "Call outcome": "Refusal",
              "Call outcome reason": "TemporarilyUnavailable",
              "Ring duration": "0",
              "Answer indicator": "No",
              "Release time": "2026-09-24T07:49:10.941Z",
              "Final local SessionID": "",
              "Final remote SessionID": "",
              "PSTN legal entity": "Broadsoft Adaption LLC",
              "PSTN vendor org ID": "0b43a1a8-2efd-4892-b301-e7a5a6d2c884",
              "PSTN vendor name": "Cisco Calling Plans",
              "PSTN provider ID": "3fac3e13-f8de-43b4-ad85-c2862ae3afe8",
              "External customer ID": "",
              "Redirecting party UUID": "",
              "Public Calling IP Address": "NA",
              "Public Called IP Address": "NA",
              "Caller ID number": "+48123210049",
              "External caller ID number": "+12542121223",
              "Device owner UUID": "",
              "Call Recording Platform Name": "",
              "Call Recording Result": "",
              "Call Recording Trigger": "",
              "Original called party UUID": "",
              "Recall type": "",
              "Auto Attendant Key Pressed": "NA",
              "Queue type": "",
              "Answered elsewhere": "",
              "Hold duration": 0,
              "Route list calls overage": "",
              "Caller Reputation Score": "",
              "Caller Reputation Service Result": "",
              "Caller Reputation Score Reason": "",
              "Interaction ID": "815baa45-a282-4b4a-af87-bdd5ebd5358c",
              "WxCC consult merge status": "",
              "ELIN": "",
              "Emergency number source": "",
              "Transfer type": "",
              "Transfer type context": "",
              "Answer reason": ""
            }
          ]
        }
        ```

        `Call outcome` and `Call outcome reason` are where a "the call failed" ticket gets answered. This one was never answered, and the reason was `TemporarilyUnavailable`.

    The full field reference is in [Reports for Your Cloud Collaboration Portfolio](https://help.webex.com/en-us/article/nmug598/Reports-for-Your-Cloud-Collaboration-Portfolio){:target="_blank"}, under **Report templates** > **Calling Detailed Call History Report**.

    !!! Warning
        This API is rate limited to **one request per minute** per token, so do not keep hitting **Send**. A second immediate request returns `429 Request rate exceeds threshold`.

        ![Bruno](./assets/bruno_23.png){ width="750" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

#### Meeting Qualities

While CDRs give you the outcome of a phone call, Meeting Qualities give you the technical telemetry of a Webex meeting. You can see exactly when a participant joined, what client they used, and their network type.

To get the qualities of a meeting, you first need the meeting's ID.

1. Create a `GET` request called `List Ended Meetings` with the URL `https://webexapis.com/v1/meetings` and these parameters, and click **Send**:

    | Parameter | Value |
    | --- | --- |
    | `meetingType` | `meeting` |
    | `state` | `ended` |
    | `max` | `5` |

    ![Bruno](./assets/bruno_24.png){ width="750" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

2. Copy the `id` of one meeting into your environment as `meetingId`:

    ![Bruno](./assets/bruno_25.png){ width="750" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

3. Create a `GET` request called `Get Meeting Qualities` with the URL `https://analytics.webexapis.com/v1/meeting/qualities`, add a `meetingId` parameter of `{{meetingId}}`, and **Send**:

    ![Bruno](./assets/bruno_26.png){ width="750" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

    You get one entry per participant, with client type, operating system, network type, join time and much more.

<!--
## Exercises

Build these in Bruno as new requests in your `WebexOne` collection. If you need help, you can check the solution.

1. List people, copy one `id` into your environment as `personId`, then get that person's details. Report the `displayName` and how many licenses they have.

    - [List People](https://developer.webex.com/admin/docs/api/v1/people/list-people){:target="_blank"}
    - [Get Person Details](https://developer.webex.com/admin/docs/api/v1/people/get-person-details){:target="_blank"}

    ??? Solution

        1. Create a `GET` request called `List People` with the URL `https://webexapis.com/v1/people`, add a `max` parameter of `5`, and **Send**. As an administrator you can call this with no filter, a regular user would have to pass `email` or `displayName`.
        2. From the `items` array, copy the `id` of one person into your environment as `personId`.
        3. Create a `GET` request called `Get Person Details` with the URL `https://webexapis.com/v1/people/{{personId}}` and **Send**.

        The list response does not include licenses. The single-person response does, in a `licenses` array. Its length is the answer.

2. List hunt groups, copy a hunt group's `id` and `locationId`, then get the details for that hunt group. Report the hunt group name and how many agents it has.

    - [Read the List of Hunt Groups](https://developer.webex.com/calling/docs/api/v1/features-hunt-group/read-the-list-of-hunt-groups){:target="_blank"}
    - [Get Details for a Hunt Group](https://developer.webex.com/calling/docs/api/v1/features-hunt-group/get-details-for-a-hunt-group){:target="_blank"}

    ??? Solution

        1. Create a `GET` request called `List Hunt Groups` with the URL `https://webexapis.com/v1/telephony/config/huntGroups`, add a `max` parameter of `10`, and **Send**.
        2. From the `huntGroups` array, copy the hunt group `id` and its `locationId` into your environment as `huntGroupId` and `locationId`. This chain needs two identifiers, because the detail endpoint is nested under the location.
        3. Create a `GET` request called `Get Hunt Group` with the URL `https://webexapis.com/v1/telephony/config/locations/{{locationId}}/huntGroups/{{huntGroupId}}` and **Send**.

        The response gives you the hunt group `name`, its number or extension, the `callPolicies` that decide how calls are distributed, and the `agents` array. The length of `agents` is the answer.

        If `huntGroups` is empty, the organization has no hunt group configured. Run the same chain against [call queues](https://developer.webex.com/calling/docs/api/v1/features-call-queue/read-the-list-of-call-queue-or-customer-assist-queues){:target="_blank"} instead, passing `hasCxEssentials=false`.

3. Reuse a `meetingId` from the ended-meetings request you already built, then list the participants of that meeting. Report how many people joined.

    - [List Meetings](https://developer.webex.com/meeting/docs/api/v1/meetings/list-meetings){:target="_blank"}
    - [List Meeting Participants](https://developer.webex.com/meeting/docs/api/v1/meeting-participants/list-meeting-participants){:target="_blank"}

    ??? Solution

        1. Send the `List Ended Meetings` request from Step 3.4 again, with `meetingType=meeting`, `state=ended`, and `max=5`. Copy the `id` of one meeting into your environment as `meetingId`.
        2. Create a `GET` request called `List Meeting Participants` with the URL `https://webexapis.com/v1/meetingParticipants`, add a `meetingId` parameter of `{{meetingId}}`, and **Send**.

        Each entry in `items` is one participant, with their `email`, `displayName`, whether they were the `host`, and their join and leave times. The number of entries is the answer.

        Like Meeting Qualities, this API only accepts a meeting that is in progress or already ended, so a scheduled meeting that never ran will fail here too.
-->

## Step 3.5: From API calls to agent tools

In Bruno you did not answer a troubleshooting question with a single request. You listed locations, copied an `id`, and asked for that location's calling config. You listed ended meetings, then asked for qualities.

That chain is the real work: one call produces the identifier the next call needs. You were the one concatenating them. Later in the lab, the agent will do that concatenation for you. You will ask a question in natural language, and the model will choose *list locations*, read the ID from the result, and call *get location* on its own. Same APIs, same order, no copy-paste.

That is only possible if the assistant can see those calls as **tools** rather than as URLs you have to type. An MCP server is not a new Webex product. It is the Webex APIs you just called, wrapped: a name, a short description, and an input schema, so the model can discover what exists and chain it.

### The knowledge behind every call

Look back at what you needed to know to complete this lab, none of which was the actual troubleshooting question:

- Which endpoint answers the question, out of hundreds in the portal
- Which parameters are mandatory, such as `orgId`, `from`, and `to` on audit events
- Where the useful values actually live, such as `actionText` nested under `data`
- That reports must be created before they can be listed, and which template IDs exist
- That Meeting Qualities is on a different host and only accepts an ended meeting instance ID

That knowledge is real. If you wanted an LLM to hit `webexapis.com` directly, you would have to teach it every URL, parameter, and quirk above, and re-teach it whenever the API changed. Wrapping each call as an MCP tool moves that knowledge into the tool description, which is why this chapter had to come first: you cannot wrap what you have not seen.

### The N × M problem

Now multiply that. Every AI application that needs Webex has to learn those details. Every other platform an AI application touches has the same kind of details. Wiring **N** applications to **M** systems by hand produces N × M pieces of fragile glue code, each maintained separately.

MCP turns that into **N + M**. Each system is exposed once as an MCP server, and every MCP-capable host speaks the same protocol to reach it.

### APIs vs MCP

| Choose Webex REST APIs when… | Choose Webex MCP when… |
| --- | --- |
| You need full control over every request | You want natural-language access from an AI client |
| Performance and custom business logic matter | You need the assistant to chain calls the way you just did in Bruno |
| You build enterprise apps with webhooks | You connect IDE or agent frameworks to Webex quickly |

These are not competing choices. MCP does not replace the APIs. The HTTP call still happens underneath, with the same token and the same JSON. MCP is how you give an agent **new capabilities** on top of APIs that already exist.

### Why you need your own server

The current official MCP servers explored before wrap messaging, meetings, and workspaces, and more, but they are user-oriented: they act on *a person's* meetings, messages, and rooms. There is no official server for Webex Calling or Control Hub troubleshooting, which is exactly the set of APIs you just called by hand, and that is the organization-level capability we are after.

In the next section will wrap them yourself: the same endpoints, the same token, now exposed as tools. The assistant will then concatenate them the way you concatenated them in Bruno, automatically.

