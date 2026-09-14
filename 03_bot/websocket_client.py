"""Webex WebSocket client: register a device and deliver incoming message events."""

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
        self.cluster, _, self.person_uuid = base64.b64decode(self.me["id"] + "==").decode().split("/")[2:]
        self.clusters = None

    def _cluster_of(self, hydra_id):
        return base64.b64decode(hydra_id + "==").decode().split("/")[2]

    def _room_clusters(self):
        clusters, url, params = [], f"{API_URL}/rooms", {"max": 100}
        for _ in range(5):
            response = self.session.get(url, params=params)
            if not response.ok:
                break
            for room in response.json().get("items", []):
                cluster = self._cluster_of(room["id"])
                if cluster not in clusters:
                    clusters.append(cluster)
            url = response.links.get("next", {}).get("url")
            if not url:
                break
            params = None
        return clusters

    def _candidate_clusters(self, activity):
        # The event's own cluster first, then the bot's, then the clusters its spaces live in.
        candidates = []
        for node in (activity, activity.get("target"), activity.get("object")):
            global_id = node.get("globalId") if isinstance(node, dict) else None
            if isinstance(global_id, str) and "/" in global_id:
                candidates.append(global_id.split("/")[0])
        candidates.append(self.cluster)
        if self.clusters is None:
            self.clusters = self._room_clusters()
        candidates.extend(self.clusters)
        return list(dict.fromkeys(candidates))

    def get_message(self, activity):
        # A space shared with another org keeps that org's cluster, not the bot's.
        for _ in range(2):
            for cluster in self._candidate_clusters(activity):
                hydra_id = base64.b64encode(f"ciscospark://{cluster}/MESSAGE/{activity['id']}".encode()).decode()
                response = self.session.get(f"{API_URL}/messages/{hydra_id}")
                if response.ok:
                    return response.json()
            self.clusters = None
        log.warning(f"Could not read message {activity['id']} in any known cluster")
        return None

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
                message = self.get_message(activity)
                if message:
                    self.on_message(message)

    def run(self):
        asyncio.run(self.listen())
