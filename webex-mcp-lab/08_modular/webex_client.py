"""Credentials and HTTP, resolved once and shared by every domain module.

This is the only file that reads environment variables and the only file that
holds the token. Domain modules receive a `WebexClient` and never see the
credential itself - which is why no tool schema, tool result, or log line in
this server can leak it.
"""

import os
import sys

import httpx

WEBEX_API = "https://webexapis.com/v1"


class WebexClient:
    """Holds Webex credentials and issues authenticated requests."""

    def __init__(self, env: dict | None = None) -> None:
        env = env if env is not None else os.environ

        # Every WEBEX_-prefixed variable, read once. This class knows nothing
        # about what any particular domain needs - domains ask, using require().
        self._settings = {k: v for k, v in env.items() if k.startswith("WEBEX_") and v}

        # The token is private. Nothing outside this class can read it.
        self._token = self._settings.pop("WEBEX_ACCESS_TOKEN", None)
        if not self._token:
            sys.exit(
                "WEBEX_ACCESS_TOKEN is not set. Copy .env.example to .env, add "
                "your token, and re-run with --env-file .env"
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
        async with httpx.AsyncClient(timeout=15) as http:
            return await http.request(method, url, headers=headers, **kwargs)


def failure(response: httpx.Response) -> dict:
    """Describe an HTTP failure in a sentence a model can relay to a person.

    Every branch returns something actionable and none of them raises, so one
    bad call never takes the server down - the next tool call still works.
    """
    if response.status_code in (401, 403):
        return {
            "error": (
                "Webex refused this request. The token is expired, or it lacks the "
                "permission this operation needs."
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
