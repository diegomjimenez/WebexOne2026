"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Webex Mercury WebSocket client with Adaptive Card support.
# diff websocket_client.py websocket_client_cards.py to see: +cardAction handling.
# Delivers messages via on_message AND card button taps via on_card,
# all over one outbound WebSocket — no webhook, no ngrok, no inbound connections.

import asyncio
import base64
import json
import logging
import ssl
import uuid

import certifi
import requests
import websockets

log = logging.getLogger(__name__)

API_URL = "https://webexapis.com/v1"
CATALOG_URL = "https://u2c.wbx2.com/u2c/api/v1/catalog?format=hostmap"
DEVICE_DATA = {
    "deviceName": "pywebsocket-client",
    "deviceType": "DESKTOP",
    "localizedModel": "python",
    "model": "python",
    "name": "python-spark-client",
    "systemName": "python-spark-client",
    "systemVersion": "0.1",
}


class WebSocketClientCards:
    """Opens a Webex Mercury WebSocket and delivers messages + card taps."""

    def __init__(self, access_token, on_message, on_card=None):            # NEW
        self.access_token = access_token
        self.on_message = on_message
        self.on_card = on_card                                              # NEW
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})
        self.me = self.session.get(f"{API_URL}/people/me").json()
        raw_id = base64.b64decode(self.me["id"] + "==").decode()
        self.cluster, _, self.person_uuid = raw_id.split("/")[2:]

    def get_message(self, activity, room_id):
        """Build a message dict with decrypted text from the REST API."""
        actor = activity.get("actor", {})
        resp = self.session.get(
            f"{API_URL}/messages", params={"roomId": room_id, "max": 1}
        ).json()
        items = resp.get("items", [])
        text = items[0].get("text", "") if items else ""
        return {
            "text": text,
            "roomId": room_id,
            "personEmail": actor.get("emailAddress", ""),
        }

    def get_card_inputs(self, activity):                                    # NEW
        """Fetch decrypted card inputs via the Conversation Service.        # NEW
        Mercury delivers inputs KMS-encrypted; we resolve the geo-id the   # NEW
        same way webex_bot does: rewrite target.url, then optionally hit   # NEW
        the public API for decryption."""                                   # NEW
        activity_id = activity.get("id", "")                               # NEW
        target = activity.get("target", {})                                # NEW
        conv_url = target.get("url", "")                                   # NEW
        conv_target_id = target.get("id", "")                              # NEW
        if not activity_id or not conv_url or not conv_target_id:          # NEW
            log.warning("cardAction missing id/target fields")             # NEW
            return {}                                                      # NEW
        # Rewrite: conversations/<conv_id> → attachment/actions/<act_id>   # NEW
        internal_url = conv_url.replace(                                   # NEW
            f"conversations/{conv_target_id}",                             # NEW
            f"attachment/actions/{activity_id}",                            # NEW
        )                                                                  # NEW
        resp = self.session.get(internal_url)                              # NEW
        if not resp.ok:                                                    # NEW
            log.warning("Internal card fetch failed (status %s): %s",     # NEW
                        resp.status_code, resp.text[:200])                  # NEW
            return {}                                                      # NEW
        data = resp.json()                                                 # NEW
        # One-call path: if the response already has decrypted inputs.     # NEW
        inputs = data.get("inputs")                                        # NEW
        if isinstance(inputs, dict):                                       # NEW
            return inputs                                                  # NEW
        # Two-call path: use the geo-id to hit the public API.            # NEW
        geo_id = data.get("id", "")                                        # NEW
        if not geo_id:                                                     # NEW
            log.warning("Internal response missing 'id' field")            # NEW
            return {}                                                      # NEW
        resp2 = self.session.get(f"{API_URL}/attachment/actions/{geo_id}") # NEW
        if resp2.ok:                                                       # NEW
            return resp2.json().get("inputs", {})                          # NEW
        log.warning("Public card fetch failed (status %s): %s",           # NEW
                    resp2.status_code, resp2.text[:200])                    # NEW
        return {}                                                          # NEW

    def send_message(self, room_id, text):
        self.session.post(f"{API_URL}/messages",
                          json={"roomId": room_id, "text": text})

    def _safe_on_message(self, msg):                                     # NEW
        """Run on_message in a worker thread with error logging."""       # NEW
        try:                                                             # NEW
            self.on_message(msg)                                         # NEW
        except Exception as exc:                                         # NEW
            log.error("on_message error: %s", exc, exc_info=True)        # NEW

    async def listen(self):
        wdm_url = self.session.get(CATALOG_URL).json()["serviceLinks"]["wdm"]
        device = self.session.post(f"{wdm_url}/devices", json=DEVICE_DATA).json()
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        async with websockets.connect(device["webSocketUrl"],
                                      ssl=ssl_context) as ws:
            await ws.send(json.dumps({
                "id": str(uuid.uuid4()),
                "type": "authorization",
                "data": {"token": f"Bearer {self.access_token}"},
            }))
            log.info("WebSocket connected — listening for messages and cards")
            loop = asyncio.get_running_loop()                            # NEW
            async for raw in ws:
                data = json.loads(raw).get("data", {})
                event_type = data.get("eventType", "")
                if event_type != "conversation.activity":
                    log.debug("skip event: %s", event_type)
                    continue
                activity = data["activity"]
                verb = activity.get("verb", "")
                actor_id = activity.get("actor", {}).get("id", "")
                log.debug("activity: verb=%s actor=%s self=%s",
                          verb, actor_id[:8], self.person_uuid[:8])
                # ── Card button tap ──────────────────────────────── NEW
                if verb == "cardAction" and self.on_card:                   # NEW
                    log.info("cardAction from %s", actor_id[:8])           # NEW
                    log.debug("RAW cardAction: %s", json.dumps(activity))  # NEW
                    # Derive room the same way as messages.                # NEW
                    card_target = activity.get("target", {})               # NEW
                    card_room = card_target.get("globalId", "")            # NEW
                    if not card_room and card_target.get("url"):           # NEW
                        card_room = card_target["url"].rsplit("/", 1)[-1]  # NEW
                    try:                                                    # NEW
                        inputs = self.get_card_inputs(activity)            # NEW
                        self.on_card(inputs, card_room)                    # NEW
                    except Exception as exc:                               # NEW
                        log.error("on_card error: %s", exc, exc_info=True)# NEW
                    continue                                               # NEW
                # ── Message ──────────────────────────────────────────
                if verb != "post":
                    continue
                if actor_id == self.person_uuid:
                    continue
                target = activity.get("target", {})
                room_id = target.get("globalId", "")
                if not room_id and target.get("url"):
                    room_id = target["url"].rsplit("/", 1)[-1]
                # Dispatch to a worker thread so the loop stays free       # NEW
                # to read cardAction frames while on_message blocks       # NEW
                # on an elicitation.                                       # NEW
                msg = self.get_message(activity, room_id)                 # NEW
                loop.run_in_executor(None, self._safe_on_message, msg)    # NEW

    def run(self):
        asyncio.run(self.listen())
