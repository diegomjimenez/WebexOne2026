# Lab 2 - Webex APIs

In this section, you will start exploring Webex REST APIs. You will do a quick review on how to use Bruno and how to call them using Python. Later, we will discuss the APIs that can be used to manage and troubleshoot an organization — status, audit, compliance, reports, calling, and meetings.

## Step 2.1 - General Webex APIs

In the previous section, we enabled our Agent to use MCP Servers to perform actions on our behalf.

At the end of the day, an MCP server is just a list of tools that our agent can use. Those tools are executing API calls. Now, we will be making those API calls ourselves.

### Webex For Developers

Navigate to:<br />

- [Webex for Developers](https://developer.webex.com/){:target="_blank"}

Use the same Webex credentials provided for the lab. 

https://developer.webex.com/messaging/docs/messaging

### Calling APIs using Bruno

### Calling APIs using Python

## Step 2.2 - Webex APIs for Troubleshooting

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

Placeholder request (update path and scopes for lab tenant):

```bash
curl -s -H "Authorization: Bearer $WEBEX_ACCESS_TOKEN" \
  "https://webexapis.com/v1/adminAudit/events?max=10" | python -m json.tool
```

### Reports

Generate usage and activity reports for analysis:

```bash
curl -s -X POST -H "Authorization: Bearer $WEBEX_ACCESS_TOKEN" \
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

Example placeholder — list recent call history:

```python
import os
import requests

TOKEN = os.getenv("WEBEX_ACCESS_TOKEN")
response = requests.get(
    "https://webexapis.com/v1/callHistory",
    headers={"Authorization": f"Bearer {TOKEN}"},
    params={"max": 5},
    timeout=30,
)
response.raise_for_status()
print(response.json())
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

## Step 2.3: The N × M problem MCP solves

Without a standard protocol, every AI application needs custom glue code for every backend system — creating fragile, exponential integration work.

MCP reduces this to **N + M** connections by providing a universal interface between AI hosts and platform capabilities.

## Step 2.4: When to use Webex APIs vs Webex MCP

| Choose Webex REST APIs when… | Choose Webex MCP when… |
| --- | --- |
| You need full control over every request | You want natural-language access from an AI client |
| Performance and custom business logic matter | You need rapid prototyping across MCP-compatible tools |
| You build enterprise apps with webhooks | You connect IDE or agent frameworks to Webex quickly |
