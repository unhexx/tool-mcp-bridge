# Solutions

Recorded 2026-10-16. This pass only. No product catalog, no model comparison, no pick.

A solution here is a way to meet the written goal: one client-side function on 127.0.0.1 that can list and invoke locally configured MCP servers. Named libraries and servers are the next pass. The fit notes below say whether a shape can satisfy that sentence. They are not a design decision.

## The slot this process already occupies

`TASK_SPECIFICATION.md` and `AGENTS.md` fix the slot. The process is a loopback HTTP function. `GET /schema` is the descriptor a model host registers. `POST /v1/invoke` runs it. The xAI facts pass already separated that slot from remote MCP: a client-side tool is an ordinary function, and a Responses item of type `mcp_call` is a server-side remote server. This package's schema is the function slot.

Anything that replaces that HTTP function with "the caller speaks MCP to us" is a different product. It can sit beside this one. It does not, by itself, satisfy the goal.

## Solution A — Keep one function, speak MCP to the children

The HTTP surface stays one function (`server_label`, `tool_name`, `arguments`, `list_only`). The child protocol changes from the private `{"tool", "arguments"}` envelope to MCP.

List, for a label, becomes that server's `tools/list` (optionally after `server/discover`). Invoke becomes `tools/call` with that name and those arguments. A finished tool error stays inside the function result as `isError: true`. A crashed child, a timeout, a broken frame, or an unknown label stays a host failure.

Why this fits the goal: one registered function, loopback, tests can cover list and stdio invoke, and a spec server can answer. The function arguments already are the namespace, so two servers can expose the same tool name without a prefix scheme.

Why it is not free:

- The current test fixture is a one-line JSON echo, not an MCP server. A real stdio peer will not pass that test, and that fixture will not pass a spec client. The facts pass recorded this.
- `list_only` today returns the configured registry, including `command`. A `tools/list` result does not include the argv. Keeping both in one response mixes an operator inventory with a model catalog.
- A complete call can be `resultType: "input_required"` rather than `complete`. On stdio the server must not write JSON-RPC requests; it asks inside the reply (`https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio`). A solution that assumes one request and one content blob has to surface that result, refuse it, or run the extra round trip. The goal does not mention elicitation.
- Stdout must be protocol only. The host reads responses and notifications. It does not write JSON-RPC responses.

This is the only shape in this note that keeps the published function and can talk to a spec server. It is not selected here.

## Solution B — Keep the private envelope

What the code does now. One subprocess per call, one JSON object in, one JSON value or raw text out, `transport != "stdio"` rejected.

It meets the current tests and the letter of "list and stdio invoke" only for children that speak that private blob. A server that writes JSON-RPC will not. The facts pass already records the gap. Leaving the envelope in place is a solution only for that private peer, not for MCP.

## Solution C — Register every tool as its own function

The host still speaks MCP, then publishes each `tools/list` entry as a separate client-side function. The model calls `server_tool` directly. There is no `server_label` argument.

The client guide says this is reasonable for a handful of tools and that it consumes the context window once the catalog is large (`https://modelcontextprotocol.io/docs/2026-07-28/develop/clients/client-best-practices`). It also says changing the tools array mid-conversation invalidates the provider's prompt cache.

It fails the written goal, which is one function. It also moves schema freshness into whoever registers functions with the model. This process would have to rewrite `/schema` whenever a child list changes. That is a different contract from the one schema document served today.

## Solution D — Several model-facing meta-tools

The same client guide's progressive pattern is a small fixed set: a catalog query, a one-tool schema fetch, and a call. A single stable `call_tool({name, args})` is the variant that keeps the tools array from changing.

Against this goal, D is A with the one function split into two or three. The HTTP service would publish more than one function, which the goal does not ask for. Folding catalog, inspect, and call into modes of the existing function is still solution A, not a second product. The guide's threshold (switch to progressive discovery around 1–5% of the context window) is a host policy for a large catalog. This repository's acceptance bar does not set that threshold.

## Solution E — Be an MCP server in front of the others

A multiplexer or router is itself an MCP server. The model host connects to it with an MCP client. It either mounts upstream tools under prefixed names, or exposes a fixed meta-tool set (list, describe, call) and forwards `tools/call`.

Secondary writeups use a stable three-way split. A proxy is 1:1 and usually bridges a transport. A router aggregates many servers and dispatches by tool name or namespace. A gateway is that router plus centralized auth, policy, and audit. Sources, both secondary: `https://apigene.ai/blog/mcp-router` and `https://www.getmaxim.ai/articles/mcp-gateway-vs-mcp-proxy-vs-mcp-server-key-differences/`. Product names in those articles are out of scope here.

E is how an MCP client such as an IDE attaches many servers without editing its own config per server. It does not implement `GET /schema` plus `POST /v1/invoke`. Choosing E would drop the client-side function slot the goal names, unless a second adapter registered that function. That second adapter is solution A again.

A local stdio-to-remote bridge is the proxy case. The local-server guide already names that class as one that has had critical flaws from a malicious endpoint. Not investigated in this pass.

## Era strategy

The spec's menu, not a library's. `https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning` and the stdio binding's backward-compatibility section.

Terms: modern is per-request `_meta` (2026-07-28 and later). Legacy is the `initialize` handshake (2025-11-25 and earlier). Dual-era implements both.

There is no negotiation handshake on the modern side. The server accepts or rejects each request. `UnsupportedProtocolVersionError` (`-32022`) lists `supported`. The client should retry with a mutually supported version, or surface an error. It must not treat that error as "this is a legacy server."

Stdio probe, for a client that supports both eras. Send `server/discover` first, with the preferred modern version in `_meta`. Three outcomes:

- `DiscoverResult`: modern. Pick from `supportedVersions` and continue.
- A recognized modern error such as `UnsupportedProtocolVersionError`: modern, wrong version. Retry. Do not fall back to `initialize`.
- Any other error, or silence until a reasonable timeout: legacy. Fall back to `initialize`.

The fallback must not be keyed to one code. Legacy servers answer an unknown pre-initialize request with an implementation-defined error (often `-32601` or `-32602`) or not at all. The era is a property of the server. The client should cache it for the life of that stdio process, and may persist it for the same configuration, re-probing if the cache later fails.

A modern-only client does not need the probe. The stdio page still recommends it: some legacy servers will run an era-ambiguous method such as `tools/call` under legacy semantics if it arrives before `initialize`. The probe fails that case on purpose.

Compatibility matrix, same versioning page:

| Client | Server | Outcome |
|---|---|---|
| Modern | Modern | Works. Discover is optional. Version mismatch is a retry. |
| Modern | Legacy | Fails. Rejection, silence, or a legacy reading of an ambiguous method. The stdio probe is how the client fails on purpose. |
| Dual-era | Modern | Works. Stay modern. |
| Dual-era | Legacy | Works. Probe error or timeout, then `initialize`. |
| Legacy | Modern | Fails. No fall-forward. `initialize` is an unknown method and lacks `_meta`. |
| Legacy | Dual-era | Works. The server answers `initialize`. |
| Legacy | Legacy | The legacy revision. Out of scope for that page. |

The Inspector publishes the same three choices as a per-server setting: `legacy`, `auto`, and `modern`. `legacy` is its default because a `server/discover` probe stalls on a silent stdio server and pollutes a debug transcript. `auto` probes and falls back. `modern` pins 2026-07-28 and does not fall back. `https://modelcontextprotocol.io/docs/2026-07-28/tools/inspector/protocol-eras`

Fit: a child fleet that can be either era is a dual-era client, with a probe timeout so silence becomes legacy instead of a hung invoke. Modern-only is smaller and misses handshake servers, which the facts pass already says are still published. Legacy-only misses 2026-07-28 servers and has no fall-forward. The goal does not name an era. The spec says a single-era client cannot cover both columns.

## Child process lifetime

Protocol statelessness is not "spawn a process per RPC." On stdio the client launches the server, holds the pipes, and shuts it down by closing stdin, waiting, then terminating. After a restart, in-flight requests are lost and the client retries them on the fresh process, because there is no protocol session to recover. `subscriptions/listen` must be opened again. `https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio`

Two host policies still fit that text:

- Hold one child per `server_label` until idle or crash, and send discover (once) and later calls on that pipe. Era cache matches "lifetime of the server process." Startup cost is paid once. A one-shot HTTP invoke reuses the child.
- Start a child for one HTTP invoke, write the messages that invoke needs, then close stdin. Correct if those messages finish before exit. Pays startup every call. Cannot keep a listen stream. A legacy fallback needs `initialize`, `notifications/initialized`, and `tools/call` in that same process, because the handshake is process-scoped.

The current code is the second policy with a single private write and `subprocess.run`. The spec's restart paragraph assumes the client can replace the process and retry the RPC. It does not require the process to die after every call.

## What "list" can mean

Three payloads, all called list in the wild:

- Operator inventory: configured labels, transport, command. This is what `list_only` returns today. It tells the caller how the child is spawned. It does not tell the model what tools exist.
- Model catalog: `tools/list` names, titles, and descriptions, grouped by label, schemas omitted or included. This is what a model needs in order to choose a tool.
- Full schema dump: every `inputSchema` inline. Same RPC, larger body. The client guide treats that dump as the thing not to inject into the model when the catalog is large. Returning it from one function is still cheap for a small registry, and it is the payload a caller needs before it can fill `arguments`.

The goal says tests for list. It does not say which payload. Replacing the inventory with `tools/list` changes the tested response. Returning both answers two different questions in one call. That choice is open.

## How failures cross the HTTP boundary

The tools page separates a tool mistake (`isError: true` on a complete result) from a protocol failure. The HTTP handler today turns an exception into HTTP 400 with a truncated traceback, and turns a bad bearer token into 401.

A solution that wants the model to repair a bad argument returns the MCP result body as the function result. A solution that wants the model host to see a transport failure uses a non-2xx HTTP status. Using 400 for both teaches the model that a date-format error and a dead process are the same kind of failure. The spec's split is the constraint. The status codes are not chosen here.

## What this pass does not decide

- Which era policy, which list payload, and which process lifetime. Those are design choices inside solution A.
- Whether elicitation, resources, prompts, or Streamable HTTP are in scope. The goal names list and stdio invoke.
- Which implementation performs solution A. Next pass.
- Code mode. It needs a sandbox and is not required by the goal.
- HTTP OAuth on a stdio child. The authorization spec says not to. Credentials for a child come from that child's environment. The invoke bearer token stays at the HTTP gate.
