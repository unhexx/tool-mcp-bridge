"""Локальный мост: одна функция mcp_call к stdio-серверам MCP.

В xAI эти вызовы не уходят. MCP_SERVERS — JSON-список:
  [{"label": "files", "transport": "stdio", "command": ["python", "-m", "demo"]}]
Пустой реестр возвращает servers: [] без дочернего процесса.
"""
from __future__ import annotations

import json
import os
from typing import Any

import anyio
from tool_http import serve

from tool_mcp_bridge import child

TOOL = "mcp_call"
SCHEMA = {
    "type": "function",
    "name": "mcp_call",
    "description": (
        "Call or list tools on a locally configured stdio MCP server. "
        "Pass server_label and tool_name to invoke; arguments is that tool's input object. "
        "Pass list_only true, or omit tool_name, to list every server's tools as name, "
        "description, and inputSchema. Does not use xAI hosted MCP. "
        "A tool error is returned with isError true. "
        "An input_required result is returned and is not completed."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "server_label": {"type": "string"},
            "tool_name": {"type": "string"},
            "arguments": {"type": "object"},
            "list_only": {"type": "boolean", "default": False},
        },
        "required": [],
    },
}


def _servers() -> list[dict[str, Any]]:
    raw = os.environ.get("MCP_SERVERS", "[]")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("MCP_SERVERS must be a JSON list")
    return data


def run(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        return anyio.run(child.dispatch, _servers(), arguments)
    except BaseExceptionGroup as exc:
        leaf = child._single_leaf(exc)
        if leaf is None:
            raise
        raise leaf from exc


def main() -> None:
    serve(TOOL, SCHEMA, run)


if __name__ == "__main__":
    main()
