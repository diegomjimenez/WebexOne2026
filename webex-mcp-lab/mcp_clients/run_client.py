"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Small runner for the MCP test-client companions in this folder.
#
# Every 0N_..._client.py calls run_client(server_script, exercise). It spawns
# the matching server from mcp_servers/, connects via mcp.Client, and runs the
# exercise. Pass --verbose on the command line to also print every raw
# JSON-RPC frame (see _verbose.py for that machinery).

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from mcp import Client, StdioServerParameters


def banner(title: str) -> None:
    """Print a section banner."""
    print(f"\n-- {title} " + "-" * max(1, 60 - len(title) - 4))


def pretty(obj: Any) -> str:
    """Pretty-print a JSON-serializable object."""
    return json.dumps(obj, indent=2, default=str)


def _flatten(exc: BaseException) -> list[BaseException]:
    """Turn an ExceptionGroup into a flat list of leaves."""
    if isinstance(exc, BaseExceptionGroup):
        out: list[BaseException] = []
        for e in exc.exceptions:
            out.extend(_flatten(e))
        return out
    return [exc]


ExerciseFn = Callable[[Client], Coroutine[Any, Any, None]]


async def _main(server_script: str, exercise: ExerciseFn, *, verbose: bool) -> None:
    server_path = str(Path(__file__).resolve().parent.parent / "mcp_servers" / server_script)
    params = StdioServerParameters(command=sys.executable, args=[server_path])

    if verbose:
        # _verbose.py holds the raw JSON-RPC frame tap; only imported on demand.
        from _verbose import verbose_stdio

        print("(verbose mode: showing raw JSON-RPC frames)\n")
        async with Client(verbose_stdio(params), mode="legacy") as client:
            await exercise(client)
    else:
        async with Client(params) as client:
            await exercise(client)


def run_client(
    server_script: str,
    exercise: ExerciseFn,
    *,
    description: str = "MCP test client",
) -> None:
    """Parse --verbose, spawn server_script, run exercise."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print every raw JSON-RPC frame exchanged with the server",
    )
    args = parser.parse_args()

    try:
        asyncio.run(_main(server_script, exercise, verbose=args.verbose))
    except KeyboardInterrupt:
        pass
    except BaseException as exc:
        # Friendly message when the server exited at startup (usually missing creds).
        leaves = _flatten(exc)
        if any("closed" in str(e).lower() or "eof" in str(e).lower() for e in leaves):
            print(
                "\nThe server closed the connection early. If credentials are "
                "missing, that is expected - the server exits at startup.\n"
                "Set WEBEX_ACCESS_TOKEN, WEBEX_ORG_ID, and WXCC_CONFIG_API_BASE "
                "in your .env to use tools that call Webex.",
                file=sys.stderr,
            )
        else:
            raise
