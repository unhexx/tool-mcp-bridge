# Open-source software

Recorded 2026-10-16. This pass only. No model comparison, no pick.

Software that can speak MCP to a local child, or that is easy to confuse with this process. Not a registry crawl. Versions were read from PyPI or npm the same day.

## Official Python SDK, `mcp` 2.3.0

PyPI project `mcp`, release 2.3.0, not yanked. License MIT. `requires_python >=3.10`. The installation page says the docs describe v2 and require Python 3.11+. Both statements are current. This repository already requires `>=3.11`, so the PyPI floor is not the tighter one. Docs: `https://py.sdk.modelcontextprotocol.io/get-started/installation/`. Package metadata: `https://pypi.org/pypi/mcp/json`.

Hard dependencies on that release, not extras: `anyio` (`>=4.9`, or `>=4.10` when `python_version >= 3.14`), `httpx2>=2.10.0`, `jsonschema>=4.20.0`, `mcp-types==2.3.0`, `opentelemetry-api>=1.28.0`, `pydantic>=2.12.0`, `pyjwt[crypto]>=2.10.1`, `python-multipart>=0.0.9`, `sse-starlette>=3.0.0`, `starlette` (`>=0.27`, or `>=0.48.0` on 3.14), `typing-extensions>=4.13.0`, `typing-inspection>=0.4.1`, `uvicorn>=0.31.1` except on emscripten, and `pywin32` on Windows. The `cli` extra adds `python-dotenv` and `typer`. A client install pulls the HTTP server stack with it. This would be the first runtime dependency. The developer venv is 3.14, so the higher `anyio` and `starlette` markers apply there. CI is 3.12, so the lower markers apply in CI.

The 1.x line is still published. The newest 1.x release on PyPI is 1.30.0. The installation page tells a package that is not ready for v2 to pin `mcp>=1.28,<2`.

What the v2 client actually does:

- `Client(StdioServerParameters(...))` is the stdio transport. Entering `async with` spawns the process. Leaving it closes stdin, waits, and kills the child if it lingers. `https://py.sdk.modelcontextprotocol.io/client/transports/`
- The child does not inherit the parent environment. The POSIX allow-list named on that page is `HOME`, `LOGNAME`, `PATH`, `SHELL`, `TERM`, and `USER`. `env=` is merged on top. A token the child needs has to be passed there. It is not taken from the host process.
- `list_tools` and `call_tool` are methods on the connected client. A URL string selects Streamable HTTP, which this goal does not use.
- `mode` (`https://py.sdk.modelcontextprotocol.io/protocol-versions/`):
  - Default `auto`: one `server/discover` at the newest version the SDK speaks. If that server returns an error, the client falls back to `initialize`. Against the docs' own example server the reported version is `2026-07-28`.
  - `legacy`: no probe. Handshake only. The same example server then reports `2025-11-25`.
  - `2026-07-28`: no probe and no handshake. `server_info` and capabilities stay empty unless `prior_discover=` is given a saved `DiscoverResult`. A handshake-era string is rejected at construction (`ValueError`, the message says to use `mode='legacy'`).
- The protocol-versions page describes fallback as "the server returns an error." It does not say what a silent stdio child does. The spec's "timeout means legacy" rule is not restated there. Silence was not tested in this pass.
- On a 2026-07-28 connection a tool can return `InputRequiredResult`. The client can hand that to `elicitation_callback` and retry the call. `mode="legacy"` is the path for a server that still sends its own JSON-RPC request. `https://py.sdk.modelcontextprotocol.io/client/callbacks/`
- `Client(mcp_server_object)` connects in memory. The transports page says to use that in tests.

Fit, not a choice: this is the maintained Python implementation of the child side of "one function that speaks MCP." It does not serve `GET /schema` or `POST /v1/invoke`. Holding the `async with` across calls is a long-lived child. Entering it inside one HTTP request is one process per invoke. The SDK does not keep a pool, and it does not copy the parent environment. The current `subprocess.run` path inherits the environment unless told otherwise. Switching clients changes that.

## Reference servers that still track the v1 SDK

These are the usual stdio fixtures. They are the handshake era, not a 2026-07-28 peer.

- `mcp-server-time` 2026.10.10 and `mcp-server-git` 2026.10.10 on PyPI. Both MIT. Both live under `https://github.com/modelcontextprotocol/servers`. `mcp-server-time` requires `mcp<2,>=1.29.0`.
- `@modelcontextprotocol/server-everything` 1.0.0 on npm. Its description is an MCP server that exercises protocol features. It depends on `@modelcontextprotocol/sdk` `^1.31.0`. The current sdk release is 1.32.1. That package's page says v1.x implements the spec through 2025-11-25, and that 2026-07-28 support is in the separate v2 packages `@modelcontextprotocol/server` and `@modelcontextprotocol/client`, not in v1.x. `https://www.npmjs.com/package/@modelcontextprotocol/sdk`. The everything server's default transport is stdio (`npx @modelcontextprotocol/server-everything`). The npm license field is `SEE LICENSE IN LICENSE`. This pass did not open that file.

A test that spawns `mcp-server-time` or `server-everything` exercises `initialize`. It does not exercise `server/discover`. A modern stdio peer is a server built on `mcp` 2.x (`MCPServer` in-process, or the same server launched on stdio). Not selected.

## Neighbors that are a different shape

Recorded so they are not treated as this repository.

- `mcp-stdio` 0.45.1, released on PyPI 2026-10-13. Summary: a stdio-to-HTTP gateway that connects MCP clients to remote HTTP MCP servers. Python `>=3.10`. License MIT. Runtime dependency: `httpx>=0.25.0`. `mcp` is only the `integration` extra (`mcp<3,>=2`). Homepage `https://github.com/shigechika/mcp-stdio`. The project text says the default mode is a local stdio process that relays to a remote HTTP server, and that `--protocol-era auto` asks that remote which revision it speaks. An MCP client that can only spawn a child uses this to reach a remote server. This process does the opposite: an HTTP function in front of local children.
- `fastmcp-remote` 4.1.0. Summary: a Python stdio bridge for remote MCP servers, powered by FastMCP. Python `>=3.10`. Same opposite direction.
- `fastmcp` 4.1.0. Summary: the fast, Pythonic way to build MCP servers and clients. License Apache-2.0. Repository `https://github.com/PrefectHQ/fastmcp`. Docs `https://gofastmcp.com`. Extras on the 4.1.0 metadata include `client`, `server`, and `code-mode`. It is a framework for writing the programs on either end of MCP. It is not a loopback function in front of a configured stdio registry.

This pass did not find another PyPI project whose own summary is a 127.0.0.1 function that lists and invokes locally configured stdio MCP servers. The lookup was the official SDK, the reference servers above, and these three neighbors. It was not an exhaustive registry search.

## What the software fixes, and what it does not

- Era policy does not have to be written from scratch if the child side is `mcp.Client`. `auto`, `legacy`, and `2026-07-28` are already the three strategies in the solutions note. `auto` is the default, and its silent-child behavior is not documented on the protocol-versions page.
- List and call come back as typed results (`tools`, `content`, `isError`), not as the raw JSON blob the current tests parse.
- Nothing here replaces `tool_http.py`. The bearer gate, the schema document, and the one function name stay in this repository.
- A modern conformance child is not `server-everything` 1.0.0 and not `mcp-server-time` 2026.10.10. Those track the v1 SDK.
- Taking the dependency, the era mode, and the process lifetime are still open. This pass does not choose them.

## Not in this pass

- Which model calls the function, and provider tool-search.
- A survey of MCP gateways beyond the three packages that collide with this slot.
- The license text inside `server-everything`.
- Whether `mode="auto"` treats a silent stdio child as legacy or as a hung call.
