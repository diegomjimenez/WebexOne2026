"""Webex WebSocket client: register a device and deliver incoming message events."""

import asyncio
import base64
import json
import ssl
import uuid

import certifi
import requests
import websockets

API_URL = "https://webexapis.com/v1"
# Host map for the org: used to find the WDM URL that issues Webex WebSocket devices.
CATALOG_URL = "https://u2c.wbx2.com/u2c/api/v1/catalog?format=hostmap"
# Payload Webex expects when creating a desktop "device" that can open Mercury.
DEVICE_DATA = {
    "deviceName": "pywebsocket-client",
    "deviceType": "DESKTOP",
    "localizedModel": "python",
    "model": "python",
    "name": "python-spark-client",
    "systemName": "python-spark-client",
    "systemVersion": "0.1",
}


class WebSocketClient:
    """Opens a Webex Mercury WebSocket and calls on_message(message) for each new post."""

    def __init__(self, access_token, on_message):
        self.access_token = access_token
        self.on_message = on_message  # callback(message) for each incoming post
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})
        self.me = self.session.get(f"{API_URL}/people/me").json()
        # REST ids are base64 of "ciscospark://<cluster>/<type>/<uuid>"; the socket uses bare uuids.
        self.cluster, _, self.person_uuid = base64.b64decode(self.me["id"] + "==").decode().split("/")[2:]

    def get_message(self, activity_uuid):
        # The socket only carries encrypted text, so read the plaintext back from the REST API.
        message_id = base64.b64encode(f"ciscospark://{self.cluster}/MESSAGE/{activity_uuid}".encode()).decode()
        return self.session.get(f"{API_URL}/messages/{message_id}").json()

    def send_message(self, room_id, text):
        # POST a text message back into the same space.
        self.session.post(f"{API_URL}/messages", json={"roomId": room_id, "text": text})

    async def listen(self):
        # 1) Ask the catalog where device registration lives for this org.
        wdm_url = self.session.get(CATALOG_URL).json()["serviceLinks"]["wdm"]
        # 2) Register a device; the response includes the Mercury WebSocket URL.
        device = self.session.post(f"{wdm_url}/devices", json=DEVICE_DATA).json()
        # 3) Verify TLS with certifi (Python's default store often misses these CAs).
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        async with websockets.connect(device["webSocketUrl"], ssl=ssl_context) as ws:
            # 4) Authorize the socket with the bot token before events start flowing.
            await ws.send(json.dumps({
                "id": str(uuid.uuid4()),
                "type": "authorization",
                "data": {"token": f"Bearer {self.access_token}"},
            }))
            # 5) Fetch each new post in plaintext and hand it to the bot.
            async for raw in ws:
                data = json.loads(raw).get("data", {})
                if data.get("eventType") != "conversation.activity":
                    continue
                activity = data["activity"]
                # Only new posts, and never the bot's own replies (avoids an echo loop).
                if activity["verb"] != "post" or activity["actor"]["id"] == self.person_uuid:
                    continue
                self.on_message(self.get_message(activity["id"]))

    def run(self):
        asyncio.run(self.listen())
