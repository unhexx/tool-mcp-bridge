# Decision: adopt mcp>=2,<3

Filed from the Decision section of `docs/design/tool-mcp-bridge-top-solution.md`. This file does not add a second decision.

### Status

Proposed.

### Context

`AGENTS.md` fixes the stack as Python 3.11+, setuptools, pytest, and Docker Compose, and says not to leave it without an ADR. The package has zero runtime dependencies. The goal requires a stdio MCP client that can talk to both the 2026-07-28 era and the handshake era. The official client is the PyPI package `mcp`, v2 line. Release 2.3.0 (2026-10-02) is the current stable used as the reference for transitive dependencies. The package metadata requires Python `>=3.10`; the SDK docs require 3.11+, which this repo already requires.

Hard dependencies recorded for 2.3.0 include `anyio` (`>=4.9`, or `>=4.10` when `python_version >= 3.14`), `httpx2>=2.10.0`, `jsonschema>=4.20.0`, `mcp-types` pinned to the same release, `opentelemetry-api`, `pydantic>=2.12`, `pyjwt[crypto]`, `python-multipart`, `sse-starlette`, `starlette` (`>=0.27`, or `>=0.48.0` on 3.14), `typing-extensions`, `typing-inspection`, and `uvicorn` (except on emscripten). A client install pulls an HTTP server stack this process will not serve with. The developer venv is 3.14, so the higher anyio and starlette markers apply there. CI and Docker are 3.12, so the lower markers apply there.

### Decision

Add `mcp>=2,<3` to `[project].dependencies` in `pyproject.toml`. Use `mcp.Client` with `StdioServerParameters` and `mode="auto"` as the only production child client. Do not import it from `src/tool_http.py`. Do not replace `ThreadingHTTPServer`. Do not add `anyio`, `starlette`, or `uvicorn` as direct dependencies.

Reject `mcp==2.3.0` as the bound. Patch and minor releases on the 2.x line are how this client picks up protocol fixes. Reject the 1.x pin. v1 is still published and does not provide the v2 `mode="auto"` client this design is adopting.

`AGENTS.md` Recommended Stack, in the same PR, gains one line: the stdio child client is `mcp>=2,<3`, with a pointer at `docs/adr/0001-mcp-sdk-stdio-client.md`, and the HTTP surface stays stdlib.

### Consequences

- First non-stdlib runtime install. Docker image `tool-mcp-bridge:local` grows by the wheel set the moment this dependency is installed, even before `run()` changes. `mem_limit: 256m` is not changed in this design. Measure idle and one-invoke RSS after the image builds; raise the limit only with that measurement, in a follow-up, if the headroom is gone. No RSS figure is claimed here.
- Transitive `starlette` / `uvicorn` / `httpx2` must not be used to grow an HTTP MCP server inside this process. Review of the implementation diffs for `streamable_http_client`, `Client(<str>)`, and a new listen socket.
- Era behavior, shutdown, and the env allow-list track the SDK. The spec's silence-means-legacy rule and the ban on falling back from `UnsupportedProtocolVersionError` are not reimplemented here.
- Rollback of the behavior PR can leave the dependency in place (the echo path does not import it). Rollback of the dependency PR returns the package to stdlib-only.
- If this decision is rejected, stop. Implement S2 against the HTTP contract in this document. Do not take a partial SDK (types only, or v1).
