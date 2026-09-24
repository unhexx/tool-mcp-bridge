"""Local MCP bridge: expose stdio/HTTP MCP tools as one client-side function.

Does not send MCP calls to xAI. Configure MCP_SERVERS as JSON list:
  [{"label": "files", "transport": "stdio", "command": ["python", "-m", "demo"]}]
Without servers, returns the registry (empty) so agents can detect local mode.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from tool_http import serve

TOOL = "mcp_call"
SCHEMA = {
    "type": "function",
    "name": "mcp_call",
    "description": "Call a tool on a locally configured MCP server. Arguments: server_label, tool_name, arguments. Does not use xAI hosted MCP.",
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
    servers = _servers()
    if arguments.get("list_only") or not arguments.get("tool_name"):
        return {
            "servers": [
                {"label": s.get("label"), "transport": s.get("transport"), "command": s.get("command")}
                for s in servers
            ]
        }
    label = arguments.get("server_label")
    tool_name = arguments.get("tool_name")
    tool_args = arguments.get("arguments") or {}
    match = next((s for s in servers if s.get("label") == label), None)
    if match is None:
        raise ValueError(f"unknown server_label: {label}")
    transport = match.get("transport", "stdio")
    if transport != "stdio":
        raise ValueError(f"transport not implemented locally: {transport}")
    command = match.get("command")
    if not isinstance(command, list) or not command:
        raise ValueError("server command required")
    payload = json.dumps({"tool": tool_name, "arguments": tool_args}, ensure_ascii=False)
    proc = subprocess.run(  # noqa: S603
        command,
        input=payload.encode("utf-8"),
        capture_output=True,
        timeout=int(os.environ.get("MCP_TIMEOUT", "20")),
        check=False,
    )
    stdout = proc.stdout.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(stdout) if stdout.strip() else {}
    except json.JSONDecodeError:
        parsed = {"raw": stdout[-4000:]}
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "result": parsed,
        "stderr": proc.stderr.decode("utf-8", errors="replace")[-2000:],
    }


def main() -> None:
    serve(TOOL, SCHEMA, run)


if __name__ == "__main__":
    main()
