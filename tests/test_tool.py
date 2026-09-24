import json
import sys
from tool_mcp_bridge.server import run


def test_list(monkeypatch):
    monkeypatch.setenv("MCP_SERVERS", json.dumps([{"label": "echo", "transport": "stdio", "command": [sys.executable, "-c", "print(1)"]}]))
    out = run({"list_only": True})
    assert out["servers"][0]["label"] == "echo"


def test_stdio_echo(monkeypatch):
    code = "import sys,json; print(json.dumps({'echo': json.loads(sys.stdin.read())}))"
    monkeypatch.setenv("MCP_SERVERS", json.dumps([
        {"label": "echo", "transport": "stdio", "command": [sys.executable, "-c", code]}
    ]))
    out = run({"server_label": "echo", "tool_name": "ping", "arguments": {"n": 1}})
    assert out["ok"] is True
    assert out["result"]["echo"]["tool"] == "ping"
