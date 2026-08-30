"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Credentials and HTTP, resolved once and shared by every domain module.

import logging
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

# One logger for the whole server. Every domain module calls
# logging.getLogger("webex") and inherits this config.
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("webex")


class WebexClient:
    """Holds Webex credentials and issues authenticated requests."""

    def __init__(self, env: dict | None = None) -> None:
        env = env if env is not None else os.environ

        # Every WEBEX_/WXCC_ setting, read once. Token stays private; the rest
        # are handed out on demand via require().
        self._settings = {
            k: v for k, v in env.items() if k.startswith(("WEBEX_", "WXCC_")) and v
        }

        self._token = self._settings.pop("WEBEX_ACCESS_TOKEN", None)
        if not self._token:
            sys.exit(
                "WEBEX_ACCESS_TOKEN is not set. Copy .env.example to .env, add "
                "your token, and re-run."
            )

    def require(self, *names: str, needed_by: str) -> dict:
        """Return the named settings, or stop the server naming the missing one."""
        for name in names:
            if name not in self._settings:
                sys.exit(f"{name} is not set. It is required by {needed_by}.")
        return {name: self._settings[name] for name in names}

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Issue an authenticated request. The caller inspects the response."""
        headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
        # URL only, never the token.
        log.debug("-> %s %s", method, url)
        async with httpx.AsyncClient(timeout=15) as http:
            response = await http.request(method, url, headers=headers, **kwargs)
        log.debug("<- HTTP %s (%s %s)", response.status_code, method, url)
        return response


def failure(response: httpx.Response) -> dict:
    """Describe an HTTP failure in a sentence a model can relay to a person."""
    if response.status_code in (401, 403):
        return {
            "error": (
                "Webex refused this request. The token is expired, or it lacks the "
                "Contact Center config permission (cjp:config_write) this operation needs."
            )
        }
    if response.status_code == 404:
        return {"error": "Webex has no such item. Check the id and try again."}
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "a few")
        return {"error": f"Rate limited by Webex. Wait {retry_after} seconds and try again."}
    if response.status_code >= 500:
        return {"error": "Webex is having trouble right now. This is worth retrying."}
    return {"error": f"Webex returned HTTP {response.status_code}."}
