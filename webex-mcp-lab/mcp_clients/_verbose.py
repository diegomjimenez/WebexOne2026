"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Advanced / optional reading. This module is imported by run_client.py only
# when --verbose is set. It wraps mcp.stdio_client so every JSON-RPC frame that
# flows in or out is printed as CLIENT -> or SERVER ->. If you just want to use
# the clients, you never need to open this file.

from __future__ import annotations

import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import anyio
from mcp import StdioServerParameters, stdio_client
from mcp.client._transport import TransportStreams
from mcp.shared.message import SessionMessage


def _frame_line(msg: SessionMessage, direction: str) -> str:
    raw = msg.message.model_dump_json(by_alias=True, exclude_unset=True)
    return f"  {direction} {raw}"


def _safe_print(text: str) -> None:
    """Print text, replacing chars the console can't encode (Windows cp1252)."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode())


@asynccontextmanager
async def verbose_stdio(
    params: StdioServerParameters,
) -> AsyncGenerator[TransportStreams, None]:
    """Wrap stdio_client so every JSON-RPC frame is printed as it goes past."""
    async with stdio_client(params) as (read_stream, write_stream):
        read_send, read_recv = anyio.create_memory_object_stream[SessionMessage | Exception](0)
        write_send, write_recv = anyio.create_memory_object_stream[SessionMessage](0)

        async def _tap_reads() -> None:
            try:
                async with read_send:
                    async for item in read_stream:
                        if isinstance(item, SessionMessage):
                            _safe_print(_frame_line(item, "SERVER ->"))
                        await read_send.send(item)
            except (anyio.ClosedResourceError, anyio.BrokenResourceError):
                pass

        async def _tap_writes() -> None:
            try:
                async with write_recv:
                    async for item in write_recv:
                        _safe_print(_frame_line(item, "CLIENT ->"))
                        await write_stream.send(item)
            except (anyio.ClosedResourceError, anyio.BrokenResourceError):
                pass

        async with anyio.create_task_group() as tg:
            tg.start_soon(_tap_reads)
            tg.start_soon(_tap_writes)
            try:
                yield read_recv, write_send
            finally:
                tg.cancel_scope.cancel()
