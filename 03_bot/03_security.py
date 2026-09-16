"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Restrict who can talk to the bot.
"""

import logging
import os

from dotenv import load_dotenv

from websocket_client import WebSocketClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("security-bot")

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("Set BOT_TOKEN in your .env file")

DENIED_DOMAIN_REPLY = "This bot only accepts messages from allowed organization domains."
DENIED_ADMIN_REPLY = "This bot only accepts messages from allowed users."

def parse_csv(value: str) -> set[str]:
    return {item.strip().lower() for item in (value or "").split(",") if item.strip()}

ALLOWED_DOMAINS = parse_csv(os.getenv("ALLOWED_DOMAINS", ""))
ALLOWED_ADMINS = parse_csv(os.getenv("ALLOWED_ADMINS", ""))

def sender_domain(email: str) -> str:
    if not email or "@" not in email:
        return ""
    return email.rsplit("@", 1)[-1].strip().lower()


def is_allowed_sender(email: str) -> bool:
    """True when no domain list is set, or the sender's domain is in ALLOWED_DOMAINS."""
    if not ALLOWED_DOMAINS:
        return True
    return sender_domain(email) in ALLOWED_DOMAINS


def is_admin(email: str) -> bool:
    """True when no admin list is set, or the sender is listed in ALLOWED_ADMINS."""
    if not ALLOWED_ADMINS:
        return True
    return (email or "").strip().lower() in ALLOWED_ADMINS

def handle_message(message):
    text = (message.get("text") or "").strip()
    if not text:
        return

    sender = message.get("personEmail") or ""
    log.info(f"Received from {sender}: {text}")

    if not is_allowed_sender(sender):
        log.warning(f"Rejected (domain): {sender}")
        bot.send_message(message["roomId"], DENIED_DOMAIN_REPLY)
        return

    if not is_admin(sender):
        log.warning(f"Rejected (user): {sender}")
        bot.send_message(message["roomId"], DENIED_ADMIN_REPLY)
        return

    reply = f"Authorized ({sender_domain(sender)}): {text}"
    bot.send_message(message["roomId"], reply)
    log.info(f"Sent to {sender}: {reply}")


if __name__ == "__main__":
    bot = WebSocketClient(access_token=BOT_TOKEN, on_message=handle_message)
    log.info(f"Listening as {bot.me['emails'][0]} via WebSocket... (Ctrl+C to stop)")
    log.info(f"Allowed domains: {', '.join(sorted(ALLOWED_DOMAINS)) or '(all)'}")
    log.info(f"Admins: {', '.join(sorted(ALLOWED_ADMINS)) or '(all)'}")
    try:
        bot.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
