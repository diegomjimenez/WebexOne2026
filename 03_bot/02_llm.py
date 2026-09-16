"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Forward incoming Webex messages to OpenAI and reply with the model output.
"""

import logging
import os

import requests
from dotenv import load_dotenv

from websocket_client import WebSocketClient

# Prefer the OS trust store (Windows/macOS/Linux) so company HTTPS inspection, whose CA
# lives there but not in certifi, still verifies. Falls back to certifi if unavailable.
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")
ERROR_REPLY = "Sorry, I could not reach the AI service right now. Please try again in a moment."

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("llm-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not BOT_TOKEN:
    raise SystemExit("Set BOT_TOKEN in your .env file")
if not OPENAI_API_KEY:
    raise SystemExit("Set OPENAI_API_KEY in your .env file")


def ask_llm(user_text: str) -> str:
    response = requests.post(
        OPENAI_URL,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_MODEL,
            "messages": [{"role": "user", "content": user_text}],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def handle_message(message):
    text = (message.get("text") or "").strip()
    if not text:
        return

    sender = message["personEmail"]
    log.info(f"Received from {sender}: {text}")

    try:
        reply = ask_llm(text)
    except requests.exceptions.SSLError:
        log.error(
            "TLS verification failed. If your company inspects HTTPS traffic, install the "
            "requirements (truststore) or point SSL_CERT_FILE at your corporate CA bundle."
        )
        reply = ERROR_REPLY
    except Exception:
        log.exception("LLM call failed")
        reply = ERROR_REPLY

    bot.send_message(message["roomId"], reply)
    log.info(f"Sent to {sender}: {reply}")


if __name__ == "__main__":
    bot = WebSocketClient(access_token=BOT_TOKEN, on_message=handle_message)
    log.info(f"Listening as {bot.me['emails'][0]} via WebSocket... (Ctrl+C to stop)")
    log.info(f"OpenAI model: {OPENAI_MODEL}")
    try:
        bot.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
