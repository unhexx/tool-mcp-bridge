# Brainstorm

Recorded 2026-10-16. Candidates only. Not a design, not reviewer consensus.

The goal is one loopback function that lists and invokes locally configured MCP servers. The research already closed the shape. What is left is which candidate the design writer should start from, and which choices stay open.

## Closed before this note

- The process is the host. One client per configured server. The model sees one function. `GET /schema` and `POST /v1/invoke` stay.
- The child must speak MCP. The private `{"tool", "arguments"}` envelope does not.
- This process is not an MCP server, not a gateway, and not a model client.
- HTTP MCP stays unimplemented.
- Stdio credentials are not the HTTP bearer token. The bearer stays on `/v1/invoke`.
- A tool mistake (`isError: true`) is not an HTTP failure. A dead child, a timeout, a bad frame, or an unknown label is.
- Both protocol eras are still in the wild. A one-era client misses the other.
- xAI tool search cannot see tools that were never declared on the model request. One function named `mcp_call` is the whole model-facing surface.

## Rejected

| Candidate | Why it loses |
|---|---|
| Keep the private envelope | Meets today's echo test. Does not talk to an MCP server. |
| One model function per child tool | Breaks the one-function goal. Hits the 350-tool cap and the prompt-cache problem the client guide describes. |
| Be the MCP multiplexer | The caller would speak MCP to us. The goal's caller speaks a function call. |
| Code mode, Streamable HTTP, elicitation UI, container-per-server | Not in the acceptance bar. |

## Candidates that can meet the goal

Both keep the function, speak JSON-RPC to a stdio child, and do it inside one process per HTTP invoke. One process per call is the shared choice: the current server is a sync request handler, a held child needs a lock and a lifetime policy, and a legacy handshake is process-scoped so discover-or-initialize and the following `tools/list` or `tools/call` must share the process anyway. A pool can be a later change. It is not required to pass list and invoke tests.

### S1 — `function-over-sdk-stdio`

Depend on `mcp` 2.x. `Client(StdioServerParameters, mode="auto")` inside `run`. Leave the context before the HTTP handler returns, so the SDK closes stdin and kills a lingering child.

List (`list_only`, or no `tool_name`) connects to each stdio entry and returns `tools/list`: name, description, inputSchema. No `command`. Invoke calls `tools/call` and returns the result body, including `isError` and `structuredContent`. `resultType: "input_required"` is returned as that body. This process has no UI and does not run the extra round trip.

Registry entry gains an optional `env` object. The SDK does not inherit the parent environment. Pass `env` through. Do not copy `os.environ`.

Tests stop using the private echo. Use the SDK's in-process server for the protocol result, and one short stdio script that answers `server/discover` or `initialize` plus `tools/list` / `tools/call` so the pipe path is real.

Cost: first runtime dependency (the 2.3.0 tree includes pydantic, anyio, httpx2, starlette, uvicorn, and the rest recorded in the software note). `AGENTS.md` says not to leave the stdlib stack without an ADR. This candidate includes that ADR. The HTTP server stays `tool_http`. The SDK is the child client only.

### S2 — `function-over-stdlib-stdio`

Same HTTP contract as S1. No new dependency. A small client in this repo writes newline-delimited JSON-RPC, reads stdout, ignores stderr, and shuts the child down by closing stdin then waiting, with `MCP_TIMEOUT` as the cap.

Era behavior is the spec's three-way probe, not a guess at one error code: `DiscoverResult` means modern, `UnsupportedProtocolVersionError` means modern and retry, anything else or silence until the timeout means `initialize`. Then `tools/list` or `tools/call`.

Same list payload, same `isError` versus HTTP split, same optional `env`, same refusal to inherit the parent environment.

Cost: we own the probe, the handshake, id matching, and framing. The software note's SDK exists because that surface is easy to get wrong. The silent-child timeout has to be inside `MCP_TIMEOUT`, not a second unbounded wait.

## Preference for the design writer

Start from **S1 `function-over-sdk-stdio`**.

The acceptance bar is list and stdio invoke against MCP servers, not a private peer. The official client already implements `auto` / `legacy` / `2026-07-28`, spec shutdown, and the env allow-list. Reimplementing that under the "no dependency" rule spends the risk on protocol compatibility, which is the part the research says is split across eras. The dependency is real and wants an ADR. It is still the smaller risk.

S2 is the fallback if the design review rejects the dependency. The HTTP contract above should be the same either way, so the tests do not care which client speaks.

## Choices the writer should not reopen

- One function. Name stays `mcp_call`. The collision with the Responses item type `mcp_call` is the model host's branch on `type`. Renaming is a break for no protocol gain.
- Loopback, bearer gate, body cap, non-stdio rejected.
- No model call, no tool search, no remote MCP, no OAuth on the child.
- List does not return `command`. The model needs name, description, and `inputSchema` in the list result, because it will not see those schemas any other way. That is one function result, not 350 tools on the model request.
- Invoke returns the MCP result on HTTP 200, including `isError: true`. Host failures stay the existing HTTP error path.
- `input_required` is returned, not completed.
- One child process per call. `MCP_TIMEOUT` bounds it.

## Still open inside S1

- Pin `mcp>=2,<3` versus `mcp==2.3.0`. The writer picks a bound. The 1.x line does not speak 2026-07-28 as a client default worth adopting.
- Whether `mode="auto"` is passed explicitly or left as the SDK default. Same behavior. Say it in the design so a later pin to `2026-07-28` is a visible change.
- How a legacy fixture is included. `mcp-server-time` and `server-everything` track the v1 SDK. A unit test can stay in-process. One stdio test should still cross the pipe. A second test for `initialize` is warranted because `auto` is the point of S1. It does not have to download npm.
- Threading: `run` is sync and the SDK client is async. `anyio.run` (or `asyncio.run`) per invoke is the obvious seam. Do not start a background loop in the HTTP server.
- Empty registry still returns an empty list, so a caller can see local mode. That behavior stays.

## Not consensus

S1 is the brainstorm's starting point. The design doc does not exist yet. A reviewer has not agreed.
