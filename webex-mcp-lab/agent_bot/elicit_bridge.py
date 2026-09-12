"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

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
                                "text": "Cisco Live!",
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
def request(message, timeout=60):
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
    # Wait for the user to tap a button.
    event = threading.Event()
    _pending[elicit_id] = {"event": event, "result": False}
    event.wait(timeout=timeout)
    confirmed = _pending.pop(elicit_id, {}).get("result", False)
    log.info("Elicitation %s: %s", elicit_id,
             "confirmed" if confirmed else "declined/timed-out")
    return confirmed


# Called by the bot when a card button is tapped.
def resolve(elicit_id, confirmed):
    entry = _pending.get(elicit_id)
    if not entry:
        return                                       # expired or duplicate tap
    entry["result"] = confirmed
    entry["event"].set()
