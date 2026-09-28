"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Elicit bridge — surface MCP elicitation as a Webex Adaptive Card.
# The server asks "are you sure?", this module posts a card with
# Confirm / Decline buttons and blocks until the user taps one.

import logging
import threading
import uuid

import requests

log = logging.getLogger(__name__)

# Module state, set by init() and set_room().
_bot_token = None
_current_room = None
# Thread-safety note: _pending is written by request() on a worker thread
# and read by resolve() on the asyncio loop thread. CPython's GIL makes dict
# get/set/pop atomic, and threading.Event is thread-safe, so no lock is
# needed for this access pattern.
_pending: dict[str, dict] = {}                       # elicit_id → {event, result}


# Store the bot token for Webex API calls.
def init(bot_token):
    global _bot_token
    _bot_token = bot_token


# Set the room to post the card into (called before each agentic_loop).
def set_room(room_id):
    global _current_room
    _current_room = room_id


# Build the Cisco Live branded Adaptive Card for an elicitation.
def card_json(message, elicit_id):
    return {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "items": [{
                                "type": "Image",
                                "style": "Person",
                                "url": "https://securitydocs.cisco.com/Site%20images%20for%20Docs%20portal/Initial%20site%20images/Temp_Cisco-logo.png",
                                "size": "Medium",
                                "height": "50px",
                            }],
                            "width": "auto",
                        },
                        {
                            "type": "Column",
                            "items": [{
                                "type": "TextBlock",
                                "weight": "Bolder",
                                "text": "webex one 2026!",
                                "horizontalAlignment": "Left",
                                "wrap": True,
                                "color": "Light",
                                "size": "Large",
                                "spacing": "Small",
                            }],
                            "width": "stretch",
                        },
                    ],
                },
                {
                    "type": "TextBlock",
                    "text": "⚠ Confirm Action",
                    "weight": "Bolder",
                    "size": "Medium",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": message,
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": "⏱ Expires in ~3 min",
                    "size": "Small",
                    "isSubtle": True,
                    "wrap": True,
                },
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "✓ Confirm",
                    "data": {"elicit_id": elicit_id, "action": "confirm"},
                },
                {
                    "type": "Action.Submit",
                    "title": "✗ Decline",
                    "data": {"elicit_id": elicit_id, "action": "decline"},
                },
            ],
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.3",
        },
    }


# Post the card and block until the user taps a button or timeout.
# NOTE: call_tool()'s timeout in utils/mcp_client.py must exceed this value
# so eliciting tools return real results to the LLM.
def request(message, timeout=180):
    elicit_id = str(uuid.uuid4())
    card = card_json(message, elicit_id)
    # POST the card to the Webex room.
    resp = requests.post(
        "https://webexapis.com/v1/messages",
        headers={"Authorization": f"Bearer {_bot_token}",
                 "Content-Type": "application/json"},
        json={"roomId": _current_room,
              "text": f"⚠ {message} (Confirm or Decline)",
              "attachments": [card]},
    )
    if not resp.ok:
        log.warning("Failed to post elicitation card: %s", resp.text)
        return False
    card_msg_id = resp.json().get("id", "")
    # Wait for the user to tap a button.
    event = threading.Event()
    _pending[elicit_id] = {"event": event, "result": False,
                           "room": _current_room,
                           "message_id": card_msg_id}
    resolved = event.wait(timeout=timeout)
    entry = _pending.pop(elicit_id, {})
    confirmed = entry.get("result", False)
    if not resolved:
        # Timeout — delete the zombie card and post expiry status.
        _delete_card(entry.get("message_id"))
        _post_status(entry.get("room"), _ACK_EXPIRED)
    log.info("Elicitation %s: %s", elicit_id,
             "confirmed" if confirmed else "declined/timed-out")
    return confirmed


# Default ack wording — in-progress, not a completion claim.
_ACK_CONFIRM = "✓ Confirmed — processing…"
_ACK_DECLINE = "✗ Declined — nothing changed"
_ACK_EXPIRED = "⏰ Confirmation expired — cancelled. Ask again to retry."
_ACK_LATE    = "⏰ That confirmation already expired — ask again to retry."


def _delete_card(message_id):
    """Delete the elicitation card message (best-effort, never raises)."""
    if not message_id or not _bot_token:
        return
    try:
        requests.delete(
            f"https://webexapis.com/v1/messages/{message_id}",
            headers={"Authorization": f"Bearer {_bot_token}"},
        )
    except Exception:
        log.warning("Failed to delete card message %s", message_id)


def _post_status(room, text):
    """Post a plain-text status line (best-effort, never raises)."""
    if not room or not _bot_token:
        return
    try:
        requests.post(
            "https://webexapis.com/v1/messages",
            headers={"Authorization": f"Bearer {_bot_token}",
                     "Content-Type": "application/json"},
            json={"roomId": room, "text": text},
        )
    except Exception:
        log.warning("Failed to post status message")


# Called by the bot when a card button is tapped.
def resolve(elicit_id, confirmed, room=None):
    entry = _pending.get(elicit_id)
    if not entry:
        # Late / expired tap — card already removed by timeout path.
        if room:
            _post_status(room, _ACK_LATE)
        return
    entry["result"] = confirmed
    entry["event"].set()
    # Delete the card and post a status line.
    _delete_card(entry.get("message_id"))
    ack_room = entry.get("room") or room
    ack = _ACK_CONFIRM if confirmed else _ACK_DECLINE
    _post_status(ack_room, ack)
