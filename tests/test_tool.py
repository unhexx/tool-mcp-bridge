import json
import logging
import sys
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from mcp.server.lowlevel.server import Server
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ElicitRequest, ElicitRequestFormParams, InputRequiredResult, ListToolsResult
from tool_http import make_handler

from tool_mcp_bridge.child import execute, stdio_params
from tool_mcp_bridge.server import SCHEMA, TOOL, run

FIXTURES = Path(__file__).parent / "fixtures"
MODERN = FIXTURES / "modern_stdio.py"
LEGACY = FIXTURES / "legacy_stdio.py"


def _text(result: dict) -> str:
    parts: list[str] = []
    for block in result.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text") or "")
    return "\n".join(parts)


def _modern_entry(env: dict | None = None) -> dict:
    entry = {
        "label": "modern",
        "transport": "stdio",
        "command": [sys.executable, str(MODERN)],
    }
    if env is not None:
        entry["env"] = env
    return entry


def test_inprocess_list_and_invoke():
    mcp = MCPServer("mem")

    @mcp.tool(description="say pong")
    def ping() -> str:
        return "pong"

    @mcp.tool(description="fails")
    def fail() -> str:
        raise ToolError("boom")

    @mcp.tool()
    def quiet() -> str:
        return "x"

    listed = execute(mcp, {"list_only": True})
    json.dumps(listed)
    assert listed["protocolVersion"] == "2026-07-28"
    assert "command" not in listed
    tools = {tool["name"]: tool for tool in listed["tools"]}
    assert set(tools) >= {"ping", "fail", "quiet"}
    for tool in tools.values():
        assert set(tool) == {"name", "description", "inputSchema"}
        assert isinstance(tool["inputSchema"], dict)
    assert tools["quiet"]["description"] is None
    assert "description" in tools["quiet"]

    ping_result = execute(mcp, {"tool_name": "ping", "arguments": {}})
    assert ping_result["resultType"] == "complete"
    assert ping_result["isError"] is False
    assert _text(ping_result) == "pong"

    fail_result = execute(mcp, {"tool_name": "fail", "arguments": {}})
    assert fail_result["resultType"] == "complete"
    assert fail_result["isError"] is True
    assert "structuredContent" in fail_result
    assert "boom" in _text(fail_result)


def test_input_required_once():
    calls = {"n": 0}

    async def on_list_tools(ctx, params) -> ListToolsResult:
        return ListToolsResult(tools=[])

    async def on_call_tool(ctx, params):
        calls["n"] += 1
        return InputRequiredResult(
            input_requests={
                "confirm": ElicitRequest(
                    method="elicitation/create",
                    params=ElicitRequestFormParams(
                        mode="form",
                        message="confirm ping",
                        requested_schema={
                            "type": "object",
                            "properties": {"ok": {"type": "string"}},
                            "required": ["ok"],
                        },
                    ),
                )
            },
            request_state="ping-state",
        )

    server = Server("input-required", on_list_tools=on_list_tools, on_call_tool=on_call_tool)
    result = execute(server, {"tool_name": "ping", "arguments": {}})
    assert "tool" not in result
    assert result["resultType"] == "input_required"
    assert result["inputRequests"]["confirm"]["method"] == "elicitation/create"
    assert result["inputRequests"]["confirm"]["params"]["message"] == "confirm ping"
    assert result["requestState"] == "ping-state"
    assert calls["n"] == 1


def test_stdio_pipe(monkeypatch):
    monkeypatch.setenv("MCP_SERVERS", json.dumps([_modern_entry()]))
    listed = run({"list_only": True})
    server = listed["servers"][0]
    assert server["protocolVersion"] == "2026-07-28"
    assert "command" not in server
    names = [tool["name"] for tool in server["tools"]]
    assert "ping" in names

    result = run({"server_label": "modern", "tool_name": "ping", "arguments": {}})
    assert _text(result) == "pong"
    assert result["resultType"] == "complete"
    assert result["isError"] is False
    assert "stderr" not in result
    assert "command" not in result


def test_legacy_initialize(monkeypatch):
    monkeypatch.setenv(
        "MCP_SERVERS",
        json.dumps(
            [
                {
                    "label": "legacy",
                    "command": [sys.executable, str(LEGACY)],
                }
            ]
        ),
    )
    listed = run({"list_only": True})
    server = listed["servers"][0]
    assert server["protocolVersion"] == "2025-11-25"
    assert len(server["tools"]) == 1
    tool = server["tools"][0]
    assert tool["name"] == "ping"
    assert tool["description"] == "pong"
    assert tool["inputSchema"] == {"type": "object", "additionalProperties": False}

    result = run({"server_label": "legacy", "tool_name": "ping", "arguments": {}})
    assert _text(result) == "pong"
    assert result["resultType"] == "complete"
    assert result["isError"] is False


def test_empty_registry(monkeypatch):
    monkeypatch.delenv("MCP_SERVERS", raising=False)
    assert run({"list_only": True}) == {"servers": []}
    monkeypatch.setenv("MCP_SERVERS", "[]")
    assert run({"list_only": True}) == {"servers": []}


def test_stdio_params_env(monkeypatch):
    monkeypatch.setenv("TOOL_TOKEN", "secret")
    monkeypatch.setenv("MCP_SERVERS", "[secret]")
    set_params = stdio_params({"command": [sys.executable, "-c", "pass"], "env": {"CHILD_ONLY": "1"}})
    assert set_params.env == {"CHILD_ONLY": "1"}
    omitted = stdio_params({"command": [sys.executable]})
    assert omitted.env is None
    assert "TOOL_TOKEN" not in (omitted.env or {})
    assert "TOOL_TOKEN" not in (set_params.env or {})


def test_env_probe(monkeypatch):
    monkeypatch.setenv("TOOL_TOKEN", "secret")
    monkeypatch.setenv("MCP_SERVERS", json.dumps([_modern_entry()]))
    omitted = run({"server_label": "modern", "tool_name": "env_probe", "arguments": {}})
    assert _text(omitted) == "TOOL_TOKEN=absent MCP_SERVERS=absent CHILD_ONLY=absent"

    monkeypatch.setenv("MCP_SERVERS", json.dumps([_modern_entry({"CHILD_ONLY": "1"})]))
    present = run({"server_label": "modern", "tool_name": "env_probe", "arguments": {}})
    assert _text(present) == "TOOL_TOKEN=absent MCP_SERVERS=absent CHILD_ONLY=present"


def test_raise_contract(monkeypatch):
    monkeypatch.setenv("MCP_SERVERS", "[]")
    with pytest.raises(ValueError, match="unknown server_label"):
        run({"server_label": "missing", "tool_name": "ping"})

    monkeypatch.setenv(
        "MCP_SERVERS",
        json.dumps([{"label": "web", "transport": "http", "command": ["python"]}]),
    )
    with pytest.raises(ValueError, match="transport not implemented locally"):
        run({"server_label": "web", "tool_name": "ping"})
    with pytest.raises(ValueError, match="transport not implemented locally"):
        run({"list_only": True})
    with pytest.raises(ValueError, match="transport not implemented locally: http"):
        execute("http://127.0.0.1:9", {"tool_name": "ping"})

    for command in ("python", ["python", 1], [], [""]):
        monkeypatch.setenv("MCP_SERVERS", json.dumps([{"label": "bad", "command": command}]))
        with pytest.raises(ValueError, match="server command required"):
            run({"server_label": "bad", "tool_name": "ping"})

    for env in (["nope"], {"A": 1}, "nope"):
        monkeypatch.setenv(
            "MCP_SERVERS",
            json.dumps([{"label": "bad", "command": ["python"], "env": env}]),
        )
        with pytest.raises(ValueError, match="server env must be an object of strings"):
            run({"server_label": "bad", "tool_name": "ping"})


def test_timeout(monkeypatch):
    monkeypatch.setenv("MCP_TIMEOUT", "1")
    monkeypatch.setenv(
        "MCP_SERVERS",
        json.dumps(
            [
                {
                    "label": "silent",
                    "command": [sys.executable, "-c", "import time; time.sleep(30)"],
                }
            ]
        ),
    )
    with pytest.raises(TimeoutError, match=r"^mcp timeout after 1s") as caught:
        run({"server_label": "silent", "tool_name": "ping", "arguments": {}})
    assert "isError" not in str(caught.value)


def test_logger_and_no_stderr_key(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="tool_mcp_bridge")
    monkeypatch.setenv("MCP_SERVERS", json.dumps([_modern_entry()]))
    result = run({"server_label": "modern", "tool_name": "ping", "arguments": {}})
    assert "stderr" not in result
    infos = [record for record in caplog.records if record.name == "tool_mcp_bridge" and record.levelno == logging.INFO]
    assert len(infos) == 1
    info = infos[0]
    assert info.label == "modern"
    assert info.op == "call"
    assert info.tool == "ping"
    assert info.protocol_version == "2026-07-28"
    assert isinstance(info.duration_ms, int)
    assert info.outcome == "ok"
    assert "stderr=" not in info.message

    caplog.clear()
    monkeypatch.setenv("MCP_TIMEOUT", "1")
    monkeypatch.setenv(
        "MCP_SERVERS",
        json.dumps(
            [
                {
                    "label": "loud",
                    "command": [
                        sys.executable,
                        "-c",
                        "import sys; sys.stderr.write('boom-stderr\\n'); raise SystemExit(1)",
                    ],
                }
            ]
        ),
    )
    with pytest.raises(Exception):
        run({"server_label": "loud", "tool_name": "ping", "arguments": {}})
    warnings = [
        record for record in caplog.records if record.name == "tool_mcp_bridge" and record.levelno >= logging.WARNING
    ]
    assert len(warnings) == 1
    warning = warnings[0]
    assert warning.label == "loud"
    assert warning.op == "call"
    assert warning.tool == "ping"
    assert isinstance(warning.duration_ms, int)
    assert warning.outcome == "error"
    assert "boom-stderr" in warning.getMessage()


def _post_invoke(body: dict) -> tuple[int, dict]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(TOOL, SCHEMA, run))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = httpd.server_address
        raw = json.dumps(body).encode("utf-8")
        conn = HTTPConnection(host, port, timeout=20)
        try:
            conn.request(
                "POST",
                "/v1/invoke",
                body=raw,
                headers={
                    "Authorization": "Bearer local",
                    "Content-Type": "application/json",
                    "Content-Length": str(len(raw)),
                },
            )
            response = conn.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, payload
        finally:
            conn.close()
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


def _keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(value)
        for item in value.values():
            found.update(_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_keys(item))
    return found


def test_http_200_for_is_error(monkeypatch):
    monkeypatch.setenv("TOOL_TOKEN", "local")
    monkeypatch.setenv("MCP_SERVERS", json.dumps([_modern_entry()]))
    status, payload = _post_invoke(
        {"arguments": {"server_label": "modern", "tool_name": "fail", "arguments": {}}}
    )
    assert status == 200
    assert payload["ok"] is True
    assert payload["tool"] == "mcp_call"
    assert payload["result"]["isError"] is True
    assert payload["result"]["resultType"] == "complete"
    assert "stderr" not in _keys(payload)
    assert "command" not in _keys(payload)


def test_http_400_for_mcp_timeout(monkeypatch):
    monkeypatch.setenv("TOOL_TOKEN", "local")
    monkeypatch.setenv("MCP_TIMEOUT", "1")
    monkeypatch.setenv(
        "MCP_SERVERS",
        json.dumps(
            [
                {
                    "label": "silent",
                    "command": [sys.executable, "-c", "import time; time.sleep(30)"],
                }
            ]
        ),
    )
    status, payload = _post_invoke(
        {"arguments": {"server_label": "silent", "tool_name": "ping", "arguments": {}}}
    )
    assert status == 400
    assert str(payload["error"]).startswith("mcp timeout after 1s")
