"""Сессия stdio: один mcp.Client на вызов, без своего конверта."""
from __future__ import annotations

import logging
import os
import tempfile
import time
from typing import Any, IO

import anyio
import tool_mcp_bridge
from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.exceptions import MCPError
from mcp.types import REQUEST_TIMEOUT, Implementation

logger = logging.getLogger("tool_mcp_bridge")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    logger.addHandler(_handler)

_CLIENT_INFO = Implementation(name="tool-mcp-bridge", version=tool_mcp_bridge.__version__)


def stdio_params(entry: dict[str, Any]) -> StdioServerParameters:
    command = entry.get("command")
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(part, str) and part for part in command)
    ):
        raise ValueError("server command required")
    raw_env = entry.get("env")
    if raw_env is None:
        env = None
    elif isinstance(raw_env, dict) and all(
        isinstance(key, str) and isinstance(value, str) for key, value in raw_env.items()
    ):
        # Копия только объекта из реестра. None — не подменять os.environ.
        env = dict(raw_env)
    else:
        raise ValueError("server env must be an object of strings")
    return StdioServerParameters(command=command[0], args=command[1:], env=env)


def as_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    dump = getattr(value, "model_dump", None)
    if dump is None:
        raise TypeError("inputSchema is not a JSON object")
    dumped = dump(mode="json", by_alias=True)
    if not isinstance(dumped, dict):
        raise TypeError("inputSchema is not a JSON object")
    return dumped


def _parse_timeout() -> int:
    timeout = int(os.environ.get("MCP_TIMEOUT", "20"))
    if timeout <= 0:
        raise ValueError("MCP_TIMEOUT must be a positive integer")
    return timeout


def _single_leaf(exc: BaseException) -> BaseException | None:
    seen = exc
    while isinstance(seen, BaseExceptionGroup) and len(seen.exceptions) == 1:
        seen = seen.exceptions[0]
    if isinstance(seen, BaseExceptionGroup):
        return None
    return seen


def _is_sdk_read_timeout(exc: BaseException) -> bool:
    code = getattr(exc, "code", None)
    if code is None and getattr(exc, "error", None) is not None:
        code = getattr(exc.error, "code", None)
    return isinstance(exc, MCPError) and code == REQUEST_TIMEOUT


def _timeout(label: str, timeout: int) -> TimeoutError:
    return TimeoutError(f"mcp timeout after {timeout}s: {label}")


async def _bounded(label: str, timeout: int, work: Any) -> Any:
    try:
        with anyio.fail_after(timeout):
            return await work()
    except BaseExceptionGroup as exc:
        leaf = _single_leaf(exc)
        if leaf is not None and (isinstance(leaf, TimeoutError) or _is_sdk_read_timeout(leaf)):
            raise _timeout(label, timeout) from exc
        if leaf is not None:
            raise leaf from exc
        raise
    except TimeoutError:
        raise _timeout(label, timeout) from None
    except MCPError as exc:
        if _is_sdk_read_timeout(exc):
            raise _timeout(label, timeout) from None
        raise


def _label_text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _tool_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    if "arguments" not in arguments or arguments["arguments"] is None:
        return {}
    tool_args = arguments["arguments"]
    if not isinstance(tool_args, dict):
        raise ValueError("arguments must be an object")
    return tool_args


async def listed_tools(client: Client) -> list[Any]:
    tools: list[Any] = []
    cursor: str | None = None
    for _ in range(32):
        page = await client.list_tools(cursor=cursor)
        tools.extend(page.tools)
        cursor = page.next_cursor
        if not cursor:
            return tools
    raise ValueError("tools/list exceeded 32 pages")


def _project(label: Any, client: Client, tools: list[Any]) -> dict[str, Any]:
    projected = []
    for tool in tools:
        # Декоратор MCPServer кладёт пропущенное описание как "". На проводе это null.
        description = tool.description or None
        projected.append(
            {
                "name": tool.name,
                "description": description,
                "inputSchema": as_json_object(tool.input_schema),
            }
        )
    return {
        "label": label,
        "transport": "stdio",
        "protocolVersion": client.protocol_version,
        "tools": projected,
    }


async def call(client: Client, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = await client.session.call_tool(
        name,
        arguments,
        allow_input_required=True,
    )
    return result.model_dump(mode="json", by_alias=True)


def _classify(op: str, result: dict[str, Any]) -> str:
    if op == "list":
        return "ok"
    if result.get("resultType") == "input_required":
        return "input_required"
    if result.get("isError") is True:
        return "is_error"
    return "ok"


def _stderr_tail(errlog: IO[Any] | None) -> str:
    # Popen берёт stderr через fileno. StringIO сюда не подходит.
    if errlog is None:
        return ""
    try:
        errlog.flush()
        errlog.seek(0)
        data = errlog.read()
    except (OSError, ValueError):
        return ""
    if isinstance(data, bytes):
        text = data.decode("utf-8", errors="replace")
    else:
        text = str(data)
    return text[-2048:]


def _emit(outcome: str, fields: dict[str, Any], tail: str | None) -> None:
    keys = ("label", "op", "tool", "protocol_version", "duration_ms", "outcome")
    message = " ".join(f"{key}={fields[key]}" for key in keys if key in fields)
    if tail:
        message = f"{message} stderr={tail}"
    level = logging.WARNING if outcome == "error" else logging.INFO
    logger.log(level, message, extra=fields)


async def _use(
    target: Any,
    *,
    label: str,
    op: str,
    tool: str,
    timeout: int,
    errlog: IO[Any] | None,
    work: Any,
) -> Any:
    if isinstance(target, str):
        raise ValueError("transport not implemented locally: http")
    started = time.perf_counter()
    protocol_version: str | None = None
    outcome = "error"

    async def body() -> Any:
        nonlocal protocol_version
        async with Client(
            target,
            mode="auto",
            read_timeout_seconds=timeout,
            client_info=_CLIENT_INFO,
        ) as client:
            protocol_version = client.protocol_version
            return await work(client)

    try:
        result = await _bounded(label, timeout, body)
        outcome = _classify(op, result)
        return result
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)
        fields: dict[str, Any] = {
            "label": label,
            "op": op,
            "tool": tool,
            "duration_ms": duration_ms,
            "outcome": outcome,
        }
        if protocol_version is not None:
            fields["protocol_version"] = protocol_version
        tail = _stderr_tail(errlog) if outcome == "error" else None
        _emit(outcome, fields, tail or None)


async def _list_one(target: Any, label: Any, timeout: int, errlog: IO[Any] | None) -> dict[str, Any]:
    async def work(client: Client) -> dict[str, Any]:
        tools = await listed_tools(client)
        return _project(label, client, tools)

    return await _use(
        target,
        label=_label_text(label),
        op="list",
        tool="",
        timeout=timeout,
        errlog=errlog,
        work=work,
    )


async def _call_one(
    target: Any,
    label: str,
    tool_name: str,
    tool_args: dict[str, Any],
    timeout: int,
    errlog: IO[Any] | None,
) -> dict[str, Any]:
    async def work(client: Client) -> dict[str, Any]:
        return await call(client, tool_name, tool_args)

    return await _use(
        target,
        label=label,
        op="call",
        tool=tool_name,
        timeout=timeout,
        errlog=errlog,
        work=work,
    )


def _stdio_target(entry: dict[str, Any]) -> tuple[Any, IO[str]]:
    params = stdio_params(entry)
    errlog = tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace")
    return stdio_client(params, errlog=errlog), errlog


async def _execute(target: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    if isinstance(target, str):
        raise ValueError("transport not implemented locally: http")
    timeout = _parse_timeout()
    label = arguments.get("server_label")
    if arguments.get("list_only") or not arguments.get("tool_name"):
        return await _list_one(target, label, timeout, None)
    tool_name = arguments["tool_name"]
    if not isinstance(tool_name, str):
        raise ValueError("tool_name must be a string")
    return await _call_one(target, _label_text(label), tool_name, _tool_arguments(arguments), timeout, None)


async def dispatch(servers: list[dict[str, Any]], arguments: dict[str, Any]) -> dict[str, Any]:
    if arguments.get("list_only") or not arguments.get("tool_name"):
        if not servers:
            return {"servers": []}
        timeout = _parse_timeout()
        listed: list[dict[str, Any]] = []
        for entry in servers:
            transport = entry.get("transport", "stdio")
            if transport != "stdio":
                raise ValueError(f"transport not implemented locally: {transport}")
            target, errlog = _stdio_target(entry)
            try:
                listed.append(await _list_one(target, entry.get("label"), timeout, errlog))
            finally:
                errlog.close()
        return {"servers": listed}
    label = arguments.get("server_label")
    tool_name = arguments.get("tool_name")
    match = next((entry for entry in servers if entry.get("label") == label), None)
    if match is None:
        raise ValueError(f"unknown server_label: {label}")
    transport = match.get("transport", "stdio")
    if transport != "stdio":
        raise ValueError(f"transport not implemented locally: {transport}")
    if not isinstance(tool_name, str):
        raise ValueError("tool_name must be a string")
    tool_args = _tool_arguments(arguments)
    timeout = _parse_timeout()
    target, errlog = _stdio_target(match)
    try:
        return await _call_one(target, _label_text(label), tool_name, tool_args, timeout, errlog)
    finally:
        errlog.close()


def execute(target: Any, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    if arguments is None:
        arguments = {}
    try:
        return anyio.run(_execute, target, arguments)
    except BaseExceptionGroup as exc:
        leaf = _single_leaf(exc)
        if leaf is None:
            raise
        raise leaf from exc
