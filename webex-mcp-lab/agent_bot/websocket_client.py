"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Webex Mercury WebSocket client — from LAB-31123.
# Opens a persistent WebSocket to Webex and delivers each new post
# to the on_message callback.

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


class WebSocketClient:
    """Opens a Webex Mercury WebSocket and calls on_message(message) for each new post."""

    def __init__(self, access_token, on_message):
        self.access_token = access_token
        self.on_message = on_message
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})
        self.me = self.session.get(f"{API_URL}/people/me").json()
        raw_id = base64.b64decode(self.me["id"] + "==").decode()
        self.cluster, _, self.person_uuid = raw_id.split("/")[2:]

    def get_message(self, activity_uuid):
        message_id = base64.b64encode(
            f"ciscospark://{self.cluster}/MESSAGE/{activity_uuid}".encode()
        ).decode()
        return self.session.get(f"{API_URL}/messages/{message_id}").json()

    def send_message(self, room_id, text):
        self.session.post(f"{API_URL}/messages",
                          json={"roomId": room_id, "text": text})

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
            log.info("WebSocket connected — listening for messages")
            async for raw in ws:
                data = json.loads(raw).get("data", {})
                if data.get("eventType") != "conversation.activity":
                    continue
                activity = data["activity"]
                if activity["verb"] != "post":
                    continue
                if activity["actor"]["id"] == self.person_uuid:
                    continue
                self.on_message(self.get_message(activity["id"]))

    def run(self):
        asyncio.run(self.listen())
