"""Credentials and HTTP, resolved once and shared by every domain module.

This is the only file that reads environment variables and the only file that
holds the token. Domain modules receive a `WebexClient` and never see the
credential itself - which is why no tool schema, tool result, or log line in
this server can leak it.
"""

import logging
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# This is the only file that reads the environment, so it is the only file that
# loads .env - no --env-file flag needed, however the server is launched.
load_dotenv()

# Logging is configured once, here, and shared by name. Every domain module
# calls logging.getLogger("webex") and gets this same logger - so the request
# log below covers all of them, and a new domain is traced the moment it makes
# its first call, with no logging code of its own. Two sinks: stderr (stdout
# carries the MCP protocol) and one file for the whole server, next to this
# source. The file is named for the server, webex-mcp-lab.log, not for this
# client. Neither sink ever sees the token, which is private to WebexClient.
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
log = logging.getLogger("webex")
log.setLevel(logging.DEBUG)
log.propagate = False
for _handler in (
    logging.StreamHandler(sys.stderr),
    logging.FileHandler(Path(__file__).parent / "webex-mcp-lab.log", encoding="utf-8"),
):
    _handler.setFormatter(logging.Formatter(LOG_FORMAT))
    log.addHandler(_handler)


class WebexClient:
    """Holds Webex credentials and issues authenticated requests."""

    def __init__(self, env: dict | None = None) -> None:
        env = env if env is not None else os.environ

        # Every credential this lab uses, read once. The token is private; the
        # rest (org id, Contact Center base) are handed out by require(). This
        # class knows nothing about what any particular domain needs.
        self._settings = {
            k: v for k, v in env.items() if k.startswith(("WEBEX_", "WXCC_")) and v
        }

        # The token is private. Nothing outside this class can read it.
        self._token = self._settings.pop("WEBEX_ACCESS_TOKEN", None)
        if not self._token:
            sys.exit(
                "WEBEX_ACCESS_TOKEN is not set. Copy .env.example to .env, add "
                "your token, and re-run."
            )

    def require(self, *names: str, needed_by: str) -> dict:
        """Return the named settings, or stop the server naming the missing one.

        Domain modules that need more than the base token call this at
        registration time, so a misconfiguration is reported once at startup
        rather than once per tool call.
        """
        for name in names:
            if name not in self._settings:
                sys.exit(f"{name} is not set. It is required by {needed_by}.")
        return {name: self._settings[name] for name in names}

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Issue an authenticated request. The caller inspects the response."""
        headers = {"Authorization": f"Bearer {self._token}"}
        # The one log line that traces every domain. Method and URL only - the
        # Authorization header, and so the token, are never in it.
        log.debug("-> %s %s", method, url)
        async with httpx.AsyncClient(timeout=15) as http:
            response = await http.request(method, url, headers=headers, **kwargs)
        log.debug("<- HTTP %s (%s %s)", response.status_code, method, url)
        return response


def failure(response: httpx.Response) -> dict:
    """Describe an HTTP failure in a sentence a model can relay to a person.

    Every branch returns something actionable and none of them raises, so one
    bad call never takes the server down - the next tool call still works.
    """
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
