"""Линейный читатель handshake-эры. stdout — только JSON-RPC."""
from __future__ import annotations

import json
import sys


def _write(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _error(req_id: object) -> None:
    _write(
        {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": "Method not found"},
        }
    )


def _result(req_id: object, result: dict) -> None:
    _write({"jsonrpc": "2.0", "id": req_id, "result": result})


def main() -> None:
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        msg = json.loads(line)
        if not isinstance(msg, dict):
            continue
        req_id = msg.get("id")
        if "id" not in msg or req_id is None:
            continue
        method = msg.get("method")
        params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
        if method == "initialize":
            _result(
                req_id,
                {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "legacy-fixture", "version": "0"},
                },
            )
            continue
        if method == "tools/list":
            _result(
                req_id,
                {
                    "resultType": "complete",
                    "tools": [
                        {
                            "name": "ping",
                            "description": "pong",
                            "inputSchema": {"type": "object", "additionalProperties": False},
                        }
                    ],
                },
            )
            continue
        if method == "tools/call" and params.get("name") == "ping":
            _result(
                req_id,
                {
                    "resultType": "complete",
                    "content": [{"type": "text", "text": "pong"}],
                    "isError": False,
                },
            )
            continue
        _error(req_id)


if __name__ == "__main__":
    main()
