"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Echo incoming Webex messages back as 'Echo: <text>' over a WebSocket.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from websocket_client import WebSocketClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("echo-bot")

load_dotenv(Path(__file__).parent / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("Copy .env.example to .env and set BOT_TOKEN")


def handle_message(message):
    # message is the decrypted Webex message: text, roomId, personEmail, ...
    text = (message.get("text") or "").strip()
    if not text:
        return

    sender = message["personEmail"]
    log.info(f"Received from {sender}: {text}")

    reply = f"Echo: {text}"
    bot.send_message(message["roomId"], reply)
    log.info(f"Sent to {sender}: {reply}")


if __name__ == "__main__":
    bot = WebSocketClient(access_token=BOT_TOKEN, on_message=handle_message)
    log.info(f"Listening as {bot.me['emails'][0]} via WebSocket... (Ctrl+C to stop)")
    try:
        bot.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
