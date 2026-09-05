#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""
Shared HTTP/JSON-RPC transport for local MCP servers.

The helpers in this directory use only the Python standard library and keep
server-specific CLI commands in separate client modules.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_PROTOCOL_VERSION = "2024-11-05"
DEFAULT_CLIENT_NAME = "room-map-rnd-mcp-client"
DEFAULT_CLIENT_VERSION = "0.1.0"


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class McpError(RuntimeError):
    """Report a transport, protocol, or remote MCP error to CLI callers."""


def validate_http_url(url: str) -> None:
    """Reject endpoints that cannot be addressed by the HTTP transport."""

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise McpError(
            f"Unsupported MCP server URL scheme: {parsed.scheme!r}."
        )
    if not parsed.netloc:
        raise McpError("MCP server URL must include a host.")


def parse_mcp_response(raw: bytes) -> dict[str, Any]:
    """Parse either plain JSON or the final data event from an MCP response."""

    text = raw.decode("utf-8", errors="replace").strip()

    if not text:
        raise McpError("Empty response from MCP server.")

    # Plain JSON response.
    if text.startswith("{"):
        return json.loads(text)

    # Streamable HTTP / SSE-style response:
    # data: {...}
    data_lines: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line.removeprefix("data:").strip()
            if payload and payload != "[DONE]":
                data_lines.append(payload)

    if not data_lines:
        raise McpError(f"Could not parse MCP response:\n{text[:1000]}")

    return json.loads(data_lines[-1])


def rpc_call(
    url: str,
    method: str,
    params: dict[str, Any] | None = None,
    request_id: int | None = 1,
    session_id: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any], str | None]:
    """Send one JSON-RPC request while preserving the negotiated session ID."""

    validate_http_url(url)

    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": method,
    }

    if request_id is not None:
        payload["id"] = request_id

    if params is not None:
        payload["params"] = params

    body = json.dumps(payload).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    if session_id:
        headers["mcp-session-id"] = session_id

    request = urllib.request.Request(
        url=url,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request, timeout=timeout_seconds
        ) as response:  # nosec B310
            response_body = response.read()
            new_session_id = (
                response.headers.get("mcp-session-id") or session_id
            )
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise McpError(f"HTTP {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise McpError(f"Could not connect to MCP server at {url}.") from exc

    parsed = parse_mcp_response(response_body)

    if "error" in parsed:
        raise McpError(
            json.dumps(parsed["error"], indent=2, ensure_ascii=False)
        )

    return parsed, new_session_id


def initialize(
    url: str,
    client_name: str = DEFAULT_CLIENT_NAME,
    client_version: str = DEFAULT_CLIENT_VERSION,
) -> str | None:
    """Negotiate one MCP session and emit the optional initialised notice."""

    _, session_id = rpc_call(
        url=url,
        method="initialize",
        params={
            "protocolVersion": DEFAULT_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {
                "name": client_name,
                "version": client_version,
            },
        },
        request_id=1,
    )

    # Some MCP servers expect this notification after initialize. It has no
    # "id", because it is a notification, not a request.
    try:
        rpc_call(
            url=url,
            method="notifications/initialized",
            params={},
            request_id=None,
            session_id=session_id,
        )
    except McpError:
        # Not all servers care; keep going if initialize itself succeeded.
        pass

    return session_id


def call_tool(
    url: str,
    tool_name: str,
    arguments: dict[str, Any],
    client_name: str = DEFAULT_CLIENT_NAME,
) -> Any:
    """Initialise a short-lived session and return one tool-call result."""

    session_id = initialize(url, client_name=client_name)
    response, _ = rpc_call(
        url=url,
        method="tools/call",
        params={
            "name": tool_name,
            "arguments": arguments,
        },
        request_id=2,
        session_id=session_id,
    )
    return response.get("result")


def list_tools(
    url: str,
    client_name: str = DEFAULT_CLIENT_NAME,
) -> None:
    """Print the tools advertised by one local MCP endpoint."""

    session_id = initialize(url, client_name=client_name)
    response, _ = rpc_call(
        url=url,
        method="tools/list",
        params={},
        request_id=2,
        session_id=session_id,
    )

    tools = response.get("result", {}).get("tools", [])
    for tool in tools:
        name = tool.get("name", "<unnamed>")
        description = tool.get("description", "").strip()
        print(name)
        if description:
            print(f"  {description}")


def print_result(result: Any) -> None:
    """Print text content directly and preserve structured results as JSON."""

    if isinstance(result, dict) and "content" in result:
        for item in result["content"]:
            if item.get("type") == "text":
                print(item.get("text", ""))
            else:
                print(json.dumps(item, indent=2, ensure_ascii=False))
        return

    print(json.dumps(result, indent=2, ensure_ascii=False))
