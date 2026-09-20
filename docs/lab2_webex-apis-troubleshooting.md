# Lab 2 - Webex APIs

In this section, you will start exploring Webex REST APIs. You will do a quick review on how to use Bruno, then create a **Service App**. That token is what you will use as soon as you need **admin** access — Control Hub, Calling numbers, audit, reports — because a Personal Access Token does not have those rights.

After that, we will look at the APIs that can be used to manage and troubleshoot an organization — status, audit, compliance, reports, calling, and meetings.

## Step 2.1 - General Webex APIs

In the previous section, we enabled our Agent to use MCP Servers to perform actions on our behalf.

At the end of the day, an MCP server is just a list of tools that our agent can use. Those tools are executing API calls. Now, we will be making those API calls ourselves.

### Webex For Developers

Navigate to [Webex for Developers](https://developer.webex.com/){:target="_blank"} and log in with your provided lab credentials.

### Get your Personal Access Token

For the simplicity of this hands-on lab, we will use your Personal Access Token (PAT). Because you are an Administrator in this sandbox, your PAT automatically inherits all your admin rights. It requires no scope configuration and lasts for 12 hours—perfect for a workshop.

1. In [Webex for Developers](https://developer.webex.com/){:target="_blank"}, in the top right corner, click your avatar and select **Copy Developer Token**.
2. Open the `.env` file at the root of your project and paste it as your `ACCESS_TOKEN`:

    ```env
    ACCESS_TOKEN=your_copied_token_here
    ```
    
    *(Note: This token expires in 12 hours. If your MCP servers stop working tomorrow, you will need to copy a fresh one.)*

https://developer.webex.com/messaging/docs/messaging

### Calling APIs using Bruno

### Calling APIs using Python

!!! Note
    A Personal Access Token acts as **you**. User-level APIs (list *your* rooms, *your* meetings) can work. As soon as you call an **admin** API — numbers, people in the org, audit, licenses — you will get `403 Forbidden` or empty data. That is expected. We fix it with a Service App before we start troubleshooting.

## Step 2.2: Production Architecture (Service Apps & Integrations)

While a Personal Access Token is perfect for a quick lab, it has a major problem for production: **It expires after 12 hours**. That is not valid for a bot that should keep running forever.

This is where **Service Apps** and **OAuth Integrations** come in.

### What is a Service App?

A Service App is a type of Webex integration designed for **machine-to-machine** communication. 

Unlike a Personal Access Token (which acts on behalf of *you*, the user), a Service App has no user context. It acts as a system or background service. This makes it the perfect choice for administrative tasks and compliance.

### Tokens and Scopes

You have already seen how scopes work. When we looked at the [Meetings MCP Server documentation](https://developer.webex.com/mcp/docs/meetings-mcp-server), we saw that the MCP token acts as a wrapper around specific permissions (like `meeting:schedules_read` or `meeting:schedules_write`). 

![Scope](./assets/scope_1.png){ width="850" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

Every Webex API requires specific scopes. How you get those scopes depends on the token type:

1. **Personal Access Token (What we are using):** The Developer Token you just copied automatically inherits *all* the scopes your user account has. Since you are an Admin, it has admin scopes.
2. **Service Apps (Production):** When you create a Service App, you must explicitly define its **scopes** to strictly limit what the machine is allowed to do. If it needs to connect to an official Webex MCP Server, it must include the `spark:mcp` scope, alongside any other API scopes the tools require.

![Scope](./assets/scope_3.png){ width="450" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}

### The Catch: User Context vs. Machine Context

Because a Service App token is just a standard Webex OAuth 2.0 Bearer token, you can pass it to an MCP Server exactly like you did with your Personal Access Token. However, there is an important difference in how the APIs behave:

1. **Personal Access Token (User Context):** 
   When you used your personal token with the `webex-list-meetings` MCP tool, the Webex API knew exactly *who* was asking. It automatically fetched *your* meetings.

2. **Service App Token (Machine Context):**
   A Service App is a faceless machine. If it calls `webex-list-meetings` without specifying a user, the API will likely return an empty list because the machine itself doesn't have a calendar. 

!!! Note "Architectural Gotcha: Analytics and Reports"
    While Service Apps are perfect for most administrative tasks, Webex Analytics and Reporting APIs strictly require **User Context**—they block Service Apps (machine-to-machine tokens) by design. 
    
    If a production AI Assistant needs to pull Analytics or Reports, it cannot use a Service App. Instead, it uses an **OAuth Integration**. The bot sends the user a "Log In" button, the human admin logs in, and the bot receives a user-bound token to pull reports on their behalf.

### The Approval Process

Because a Service App operates at a machine level and can access organization-wide data, it requires strict security oversight. A Webex Administrator must explicitly review the requested scopes and authorize the specific Service App in Control Hub before it can generate any tokens.

*(For this lab, we are skipping the Service App creation process to avoid managing scopes and approvals. We will rely entirely on your Personal Access Token.)*

??? Note "Reference: How to Create a Service App"
    If you ever need to create a Service App for a production environment, here is how you do it:
    
    1. Log into [developer.webex.com](https://developer.webex.com/){:target="_blank"}.
    2. In the top right corner of the page, click your avatar and then select [My Webex Apps](https://developer.webex.com/my-apps){:target="_blank"}.
    3. Click **Create a New App**.
    4. On the ‘Create a New App’ page, find the Service App card and click the ‘Create a Service App’ button.
    
        ![Service App](./assets/bot_1.png){ width="850" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;" }
    
    5. Enter the necessary information (Name, Icon, Description, Contact Email).
    6. Select the **Scopes** your machine needs. For example, to read phone numbers, you would need `spark-admin:telephony_config_read`.
    7. Once created, you will get a **Client ID** and **Client Secret**.
    8. At the top, in the `Admin Authorization` section, click on **Request admin authorization**.
    
        ![Service App](./assets/serviceapp_3.png){ width="900" style="display: block; margin: 0 auto; border: 1px solid lightgray; border-radius: 8px;"}
    
    9. A Webex Administrator must then go to **Collaboration Control Hub** -> **Apps** -> **Service Apps**, select your app, and click **Authorize**.
    10. Finally, you return to the Developer Portal, select your Org under **Org Authorizations**, enter your Client Secret, and click **Generate tokens** to get your 14-day `access_token` and 90-day `refresh_token`.

    **How to Refresh a Service App Token**
    
    Unlike a Personal Access Token which simply expires, a Service App token can be refreshed programmatically using the `refresh_token`.
    
    You can refresh your **access_token** by making a POST request to the Webex API:
    
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

## Step 2.3: Using the token to call an API

Now, we will test that your token works by making a standard REST API call using **Bruno** (or Postman). 

To demonstrate Control Hub management capabilities, we will use the **Numbers API** to list the phone numbers configured in the organization. This is a typical administrative task.

1. Open **Bruno** and create a new `GET` request.
2. Set the URL to: `https://webexapis.com/v1/telephony/config/numbers`
3. Go to the **Headers** tab and add:
   * **Name**: `Authorization`
   * **Value**: `Bearer YOUR_ACCESS_TOKEN` (replace with the token from your `.env` file)
4. Click **Send**.

**Equivalent cURL command:**
```bash
curl -s -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  "https://webexapis.com/v1/telephony/config/numbers" | python -m json.tool
```

You should receive a JSON response containing a list of phone numbers in your organization, proving you are successfully authenticating and retrieving organizational data.

## Step 2.4 - Webex APIs for Troubleshooting

You now have a token with **admin** scopes. Use the `ACCESS_TOKEN` in Bruno for the calls below. The Webex Status API is public and does not need a token.

### Webex Status API

Check platform health before deep-diving into org-specific issues.

Reference: [Webex Status API](https://developer.webex.com/calling/docs/webex-status-api){:target="_blank"}

```bash
curl -s https://status.webex.com/api/v2/status.json | python -m json.tool
```

Typical checks:

- Status summary and component rollup
- Unresolved incidents
- Scheduled maintenance

!!! Note "Screenshot needed"
    Add screenshot of status summary JSON or Control Hub status page alongside API output.

### Audit and compliance

| API area | Use case |
| --- | --- |
| Admin Audit Events | Track configuration changes and admin actions |
| Compliance Events | Monitor messaging and room events as compliance officer |
| Security Audit Events | Review security-related admin activity |

```bash
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://webexapis.com/v1/adminAudit/events?max=10" | python -m json.tool
```

### Reports

Generate usage and activity reports for analysis:

```bash
curl -s -X POST -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reportTemplateId": "REPLACE_WITH_TEMPLATE_ID"}' \
  https://webexapis.com/v1/reports | python -m json.tool
```

!!! Note
    Report templates and scopes vary by license. Your lab instructor will provide the template IDs available in the lab org.

### Calling and meetings troubleshooting

| Scenario | API starting point |
| --- | --- |
| Call quality investigation | Detailed Call History, Meeting Qualities |
| Agent / queue issues | Calling Service Settings, Call Routing APIs |
| Meeting attendance / stats | Meetings, Meeting Participants |

Example — list phone numbers (same call as Step 2.3):

```bash
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://webexapis.com/v1/telephony/config/numbers" | python -m json.tool
```

### Troubleshooting guide

Review the official guide for diagnostic workflows:

- [Webex API Troubleshooting Guide](https://developer.webex.com/explore/docs/api/guides/troubleshooting){:target="_blank"}

Suggested lab activities (from session deck):

1. Check general Webex Status
2. Review admin audit events
3. Create a report and download it
4. Review compliance events
5. Retrieve call history and meeting statistics

## Exercises

TBC

---

## Step 2.5: The N × M problem MCP solves

Without a standard protocol, every AI application needs custom glue code for every backend system — creating fragile, exponential integration work.

MCP reduces this to **N + M** connections by providing a universal interface between AI hosts and platform capabilities.

## Step 2.6: When to use Webex APIs vs Webex MCP

| Choose Webex REST APIs when… | Choose Webex MCP when… |
| --- | --- |
| You need full control over every request | You want natural-language access from an AI client |
| Performance and custom business logic matter | You need rapid prototyping across MCP-compatible tools |
| You build enterprise apps with webhooks | You connect IDE or agent frameworks to Webex quickly |
