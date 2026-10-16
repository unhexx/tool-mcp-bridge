# Current-version facts

Recorded 2026-10-15. This pass only. No framework comparison, no solution pick.

Sources are primary pages fetched the same day, plus the working tree. Claims that conflicted across search snippets were rechecked on the canonical URL.

## This repository

Package `tool-mcp-bridge` 1.0.0. `requires-python >= 3.11`. Runtime dependencies: none. Dev extra: `pytest>=8,<9`. Build: setuptools. Console script `tool-mcp-bridge` points at `tool_mcp_bridge.server:main`.

Local interpreter in `.venv`: Python 3.14.7. GitHub Actions (`.github/workflows/test.yml`) installs and tests on Python 3.12 only.

Git: branch `main` tracks `origin/main`. One commit, `149e614`, message `feat: локальный клиентский Tool tool-mcp-bridge`, author Evgeniy Chistyakov `<unhandled@exception.expert>`. Uncommitted at the time of this pass: modified `.gitignore`; untracked `.agent/`, `AGENTS.md`, `Agent-Init.sh`, `TASK_SPECIFICATION.md`. No design doc existed.

Agentix loop state (`.agent/LOOP_STATE.md`): cycle 0, role Orchestrator, status READY, template 3.13.0. `PROJECT_CONTEXT.md` says phase bootstrap. `.agent/TODO.md` still has both items open (confirm the goal, run the first cycle). Goal text, from `TASK_SPECIFICATION.md` and `AGENTS.md`: expose locally configured MCP servers as one client-side function on 127.0.0.1, with tests for list and stdio invoke. Out of scope: vendoring `agentic_loop_template`.

### What the code actually does

HTTP surface is stdlib only (`src/tool_http.py`):

- `ThreadingHTTPServer`. Default bind `TOOL_HOST=127.0.0.1`, `TOOL_PORT=8090`. Docker sets `TOOL_HOST=0.0.0.0` and `TOOL_PORT=8096`, and Compose publishes `127.0.0.1:8096:8096`.
- `GET /healthz` and `GET /health` return `{status, tool, mode: local}`.
- `GET /schema` returns the function descriptor. No auth.
- `POST /v1/invoke` and `POST /invoke` require `Authorization: Bearer <TOOL_TOKEN>` when the token is non-empty. Default token is the string `local`. Body cap is 2_000_000 bytes. The handler reads `arguments` if present, otherwise the whole JSON object. Failures return HTTP 400 with `error` and a truncated traceback. Auth failures return HTTP 401.
- Docker: non-root uid 10001, `no-new-privileges`, `cap_drop: ALL`, read-only root, tmpfs `/tmp`, memory 256m, pids 128. Healthcheck hits `http://127.0.0.1:8096/healthz`.

The registered function (`src/tool_mcp_bridge/server.py`) is named `mcp_call`. Parameters: `server_label`, `tool_name`, `arguments`, `list_only`. None are required.

`MCP_SERVERS` is a JSON list in the environment. Each entry is expected to carry `label`, `transport`, and `command`.

- `list_only` true, or `tool_name` missing, returns the registry. The list includes `command`, so the process argv is part of the response.
- Invoke looks up `server_label`. Only `transport == "stdio"` is accepted. Anything else raises `transport not implemented locally`.
- The call is one `subprocess.run`: stdin is a single JSON object `{"tool": tool_name, "arguments": tool_args}`, stdout is parsed as one JSON value or kept as `raw`, timeout is `MCP_TIMEOUT` seconds (default 20). The child is not kept alive. There is no second message.

Tests (`tests/test_tool.py`) cover that list path and that one-shot echo. The fixture command is `python -c` printing one JSON line. It is not an MCP server. There is no test for the HTTP server, auth, the payload cap, a non-stdio transport, a timeout, or a non-zero exit.

The process does not call the xAI API. `README.md` says `GET /schema` is the function descriptor to register beside server-side tools, and that a model call must be completed with `POST /v1/invoke`. The documented mixing section is `https://docs.x.ai/developers/tools/advanced-usage#mixing-server-side-and-client-side-tools`.

### Gap against the protocol this package claims to bridge

The invoke path is not MCP. It does not send JSON-RPC. It does not speak `initialize` / `notifications/initialized` (handshake era) or `server/discover` (current era). It does not call `tools/list` or `tools/call`. It writes a private envelope on stdin and reads one stdout blob. A server that follows the spec and writes only JSON-RPC to stdout will not satisfy `test_stdio_echo`, and the echo fixture will not satisfy a real MCP client.

## MCP specification, current revision

Fetched 2026-10-15.

- Latest revision is **2026-07-28**. `https://modelcontextprotocol.io/specification/latest/basic/transports` resolves to the 2026-07-28 transports overview and labels that version latest. The learn page states the current protocol version is 2026-07-28: `https://modelcontextprotocol.io/docs/learn/versioning` (redirects to `/docs/2026-07-28/learn/versioning`).
- Two standard transports. **stdio**: client launches the server as a subprocess; newline-delimited JSON-RPC on stdin/stdout. **Streamable HTTP**: one HTTP POST per client message to a single MCP endpoint; the response is either one JSON object or a request-scoped SSE stream. Custom transports are allowed if they keep the JSON-RPC format, the message patterns, and the per-request metadata model. A reliable byte stream should reuse stdio framing.
- On this revision, protocol version and client capabilities travel in the request body under `_meta` (`io.modelcontextprotocol/protocolVersion`). Streamable HTTP also requires the `MCP-Protocol-Version` header to match that field. Negotiation is per request. `server/discover` is a mandatory RPC the server must answer, and an optional probe for the client. If the server does not support the requested version it returns `UnsupportedProtocolVersionError` with the versions it does support.
- 2026-07-28 removed the connection-scoped `initialize` handshake and the model where servers initiate JSON-RPC requests. Clients that still talk to 2025-11-25 and earlier must detect that era and fall back. The transports overview says the body is the source of truth and that servers do not initiate JSON-RPC requests.
- Handshake-era spec remains published and final-shaped at `https://modelcontextprotocol.io/specification/2025-11-25`. Its lifecycle is still `initialize` then `notifications/initialized`, with the client proposing `protocolVersion` (example in that page: `2025-11-25`). A search snippet that called 2025-11-25 "current" was a stale learn page; the live learn page now says 2026-07-28.
- Prior remote transport HTTP+SSE (2024-11-05) was replaced by Streamable HTTP in 2025-03-26. The 2026-07-28 Streamable HTTP page says that revision also removed the standalone GET stream and protocol-level sessions: `https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http`.

Not checked this pass: the text of any draft newer than 2026-07-28. "Latest" on the spec site resolved to 2026-07-28.

## Official Python SDK

- Package name on PyPI: `mcp`. Current stable line is **v2**. Release **2.3.0** dated 2026-10-02. Prior stables seen in the release history: 2.2.0 (2026-09-07), 2.1.1 (2026-08-25), 2.1.0 (2026-08-24), 2.0.1 (2026-08-26), 2.0.0 (2026-07-28). The 1.x line is still published (1.30.0 on 2026-09-07). Docs tell dependents that are not ready for v2 to pin `mcp>=1.28,<2`.
- Docs: `https://py.sdk.modelcontextprotocol.io/`. Requirements stated there: Python 3.11+. Install: `pip install "mcp[cli]"` or `uv add "mcp[cli]"`. Documented runtime pieces: `anyio` (asyncio or trio), `pydantic`, `httpx2` for the HTTP client transports. v2.3.0 release notes require `httpx2>=2.10.0`.
- Client API documented at `https://py.sdk.modelcontextprotocol.io/client/` and `https://py.sdk.modelcontextprotocol.io/protocol-versions/`: `from mcp import Client`, used as `async with Client(target)`. Default `mode="auto"` sends `server/discover` at the newest version the SDK speaks and, if the server rejects that method, falls back to the `initialize` handshake. `mode="legacy"` forces the handshake (documented result against their example server: `2025-11-25`). `mode="2026-07-28"` pins the modern version and sends no negotiation. `client.protocol_version` reports which era connected. The SDK speaks stdio and Streamable HTTP (SSE remains for older servers).
- This repo does not depend on `mcp`. Nothing in `src/` imports it.

Adjacent, not a Python fact: the TypeScript SDK npm page for `@modelcontextprotocol/sdk` 1.32.1 (published about 2026-10-05) says v1.x implements the spec through 2025-11-25, and that 2026-07-28 support lives in v2 as separate `@modelcontextprotocol/server` and `@modelcontextprotocol/client` packages. v1.x bugfix window is at least six months after the 2026-07-27 v2 release. Source: `https://www.npmjs.com/package/@modelcontextprotocol/sdk`.

## xAI client-side contract this process sits behind

Fetched `https://docs.x.ai/developers/tools/advanced-usage` on 2026-10-15.

- Mixing is supported. Server-side tools run on the xAI side. A client-side tool is an ordinary function definition. When the model calls it, that request pauses and returns the call to the application. The application runs the function and sends the result back (`tool_result` in the xAI SDK, or a Responses item `type: function_call_output` with `call_id`).
- Detection: xAI SDK `get_tool_call_type(tool_call) == "client_side_tool"`. Responses API: an output item with `type == "function_call"` is client-side. Items typed `mcp_call` are server-side remote MCP, not the local function. The same page's example model string is `grok-4.7`. Continuation is either `previous_response_id` (with `store_messages=True`) or appending encrypted content.
- `max_turns` counts only assistant/server-side turns inside one request. A client-side call ends that request; the follow-up starts a new count.
- The page says this mixed loop is not supported in the Vercel AI SDK; it shows the xAI SDK and the OpenAI SDK pointed at `https://api.x.ai/v1`.
- Remote MCP is a different product surface. A secondary writeup dated 2026-10-14 (`https://metagrok.io/how-to/connect-remote-mcp-in-grok-api`) describes a tools entry `type: mcp` with required `server_url` and `server_label` on `POST https://api.x.ai/v1/responses`, and says only Streaming HTTP and SSE connect, so a local stdio server will not. Treat the transport restriction as secondary until the primary remote-MCP guide is read. It matches the primary page's split: `mcp_call` is server-side, `function_call` is local.

This package's `GET /schema` shape (`type: function`, `name: mcp_call`, JSON Schema `parameters`) matches the client-side function slot, not the remote `type: mcp` tool. The name `mcp_call` collides with the Responses output type used for server-side MCP. That is a naming fact, not a recommendation.

## Facts that constrain the later design

- The acceptance bar already written down is list plus stdio invoke, loopback only, one client-side function. HTTP MCP is explicitly unimplemented.
- A real stdio server speaks newline-delimited JSON-RPC and must not print logs on stdout. The current child protocol and the current test fixture do the opposite.
- Servers in the wild can be either era. The current Python SDK's default client already probes and falls back. Handshake-era code that only speaks 2025-11-25 will miss 2026-07-28 servers, and the reverse is also true.
- Adding the official SDK would be the first runtime dependency. The package today is stdlib plus pytest.
- Python floor is 3.11 in both this package and the current SDK docs. CI is 3.12. The developer venv is 3.14.7. No fact here says 3.14 is covered by CI.
