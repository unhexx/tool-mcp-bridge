"""Современный stdio-сервер для pipe-теста. Логи только в stderr."""
from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

mcp = MCPServer("modern-fixture")


@mcp.tool(description="pong")
def ping() -> str:
    return "pong"


@mcp.tool(description="boom")
def fail() -> str:
    raise ToolError("boom")


@mcp.tool()
def env_probe() -> str:
    def flag(key: str) -> str:
        return "present" if key in os.environ else "absent"

    return (
        f"TOOL_TOKEN={flag('TOOL_TOKEN')} "
        f"MCP_SERVERS={flag('MCP_SERVERS')} "
        f"CHILD_ONLY={flag('CHILD_ONLY')}"
    )


if __name__ == "__main__":
    mcp.run()
