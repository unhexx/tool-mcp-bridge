# Frameworks

Recorded 2026-10-15. This pass only. No solution pick, no open-source catalog, no model comparison.

Sources are the 2026-07-28 specification and the versioned docs fetched the same day. The OWASP cheat sheet is secondary and is used only where it cites those pages. Claims that conflicted across search snippets were rechecked on the canonical URL.

## What this pass means by a framework

A framework here is a named structure the later design has to fit: who owns orchestration, what bytes go to a child, how tools are discovered and shown to a model, and which security rules apply to a local stdio peer. Named products, SDKs, and models are later questions.

## Client-host-server

`https://modelcontextprotocol.io/specification/2026-07-28/architecture`

MCP is a client-host-server architecture. The host creates and manages multiple clients. Each client communicates with exactly one server. The host enforces security policy and consent, handles user authorization decisions, coordinates the model, and aggregates context. A client attaches the protocol version and capabilities to every request, routes messages, and keeps a security boundary between servers. Servers expose resources, tools, and prompts, stay focused, and must not read the conversation or see other servers. Cross-server interaction stays with the host.

The same page's design principles: servers should be easy to build and composable; the host owns orchestration; features are added by capability negotiation rather than by assuming a session-wide contract. The protocol is stateless. Every request carries its own protocol version and capabilities.

The learn overview restates the split and adds the transport consequence: a local stdio server typically serves one client, and a remote Streamable HTTP server typically serves many. Two layers sit under that split. The data layer is JSON-RPC 2.0 (discovery, capabilities, tools, resources, prompts, notifications). The transport layer is framing, connection setup, and authorization. `https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture`

Constraint, not a pick: this process is a host. `server_label` names which 1:1 client to use. The configured command is the server. The host does not hand the model conversation to that child.

## stdio message and process framework

`https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio`

The client launches the server as a subprocess. Messages are newline-delimited JSON-RPC and must not contain embedded newlines. The server reads JSON-RPC from stdin and writes only valid MCP messages to stdout. Logging goes to stderr. The client may capture stderr and should not treat it as an error. The client must not write non-MCP bytes to stdin. It writes requests and notifications only, and must not write JSON-RPC responses. That matches the architecture note that a server asks for user input with `InputRequiredResult` inside a reply, rather than by opening its own request.

Shutdown on that page: the client should close the child's input stream, wait for exit, and forcibly terminate if it does not exit in time. On POSIX the escalation named there is SIGTERM then SIGKILL.

The same binding says the wire format is one newline-delimited JSON-RPC message per line over a reliable bidirectional byte stream, and that custom transports on such a stream should reuse it. Logs on stdout break the framing. A private envelope is not this format.

Tension left open on purpose: the 2026 revision makes each RPC self-contained, but the stdio binding still has the client launch a subprocess and shut it down by closing stdin. One process per call and one long-lived process per server are both outside this pass.

## Per-request discovery

`https://modelcontextprotocol.io/specification/2026-07-28/server/discover`

`server/discover` is mandatory for servers and optional for clients. The request body is only standard `_meta`: `io.modelcontextprotocol/protocolVersion`, `clientInfo`, and `clientCapabilities`. The response carries `supportedVersions`, `capabilities`, server identity, optional `instructions`, and cache hints `ttlMs` and `cacheScope`. A client may skip discover and call another method directly. If the server does not support the requested version it rejects the request with `UnsupportedProtocolVersionError` and lists the versions it does support. The client retries with a mutually supported version.

Capability negotiation on the architecture page is per request, not per connection. Servers advertise tools, resources, and prompts. Clients advertise what they will accept, such as elicitation. Both sides must respect the declarations they actually sent.

The previous era is a different lifecycle, not a section of this revision. Handshake-era clients still open with `initialize` and `notifications/initialized`. A client framework that speaks only one era misses the other. That fact is already recorded; this pass does not re-open SDK behavior.

## Tool primitive

`https://modelcontextprotocol.io/specification/2026-07-28/server/tools`

A server that declares the `tools` capability must answer `tools/list`. The set may be empty and may change over time. It must not vary per connection, and it must not change as a side effect of other requests on that connection. Listing supports pagination and caching. A complete list result has `resultType: "complete"`, a `tools` array, and may include `ttlMs` and `cacheScope`.

Each tool has a `name`, human-facing title and description, and an `inputSchema`. The schema must be a JSON Schema object. For a tool with no parameters the recommended schema is `{ "type": "object", "additionalProperties": false }`. `outputSchema` is optional. The default dialect is JSON Schema 2020-12 when `$schema` is absent. Annotations that describe tool behavior are optional and, under the spec's key principles, untrusted unless the server is trusted.

`tools/call` takes `name` and `arguments`. A finished call returns `resultType: "complete"`, a `content` array, and `isError`. Failures the model can correct (validation, business rules) use `isError: true` inside a successful JSON-RPC result. They are not transport failures. Structured output is a separate `structuredContent` value that must conform to `outputSchema` when one exists, and should also be copied into a text content block. A result of `resultType: "input_required"` asks the client for elicitation inside that reply. This pass records the result type only. It does not design an elicitation loop.

When the tool list changes, a server that declared `listChanged` should notify clients that have opened a `subscriptions/listen` stream with `toolsListChanged: true`. The method is `notifications/tools/list_changed`. There is no session-scoped push on a process that exits after one request.

Client obligations written on the tools page: prompt for confirmation on sensitive operations, show tool inputs before calling, validate results before they reach the model, follow the spec's `$ref` rules when validating against `inputSchema` and `outputSchema`, implement timeouts, and log tool use.

Key principles of the same revision (`https://modelcontextprotocol.io/specification/2026-07-28`): users must consent to data access and operations; hosts must obtain explicit user consent before exposing user data to servers; hosts must obtain explicit user consent before invoking any tool; tool annotations are untrusted unless the server is trusted.

## How a host shows many tools through few model-facing functions

`https://modelcontextprotocol.io/docs/2026-07-28/develop/clients/client-best-practices`

The page is about the host, not about a server SDK. Loading every connected server's tool definitions into the model context up front wastes the window once the registry is large. It names two patterns.

Progressive discovery controls when definitions enter context. The host still fetches them with `tools/list`, but does not inject them all. It exposes a small catalog meta-tool (the example is `search_tools`) that returns names and one-line descriptions, then a detail fetch for one tool, then the real call. Retrieval inside the catalog can be keyword, embedding, a smaller model, or a hybrid. The page says to prefer a provider's built-in tool search when one exists, and to build a host search only when it does not, or when ranking must enforce access control. It suggests switching from full injection to progressive discovery at a context-window threshold on the order of 1% to 5%, and only when definitions are large. A small registry can be injected whole.

Guidelines on that page: offer more than one detail level, cache definitions in the host so a later inject does not repeat `tools/list`, treat a cached list as stale when `list_changed` arrives even if `ttlMs` has not expired, and group tools by source server. Those cache hints are the spec's caching utility, referenced from the same page.

Prompt-cache interaction on that page: providers cache the prompt prefix, including the tools array. Adding or removing definitions mid-conversation invalidates that cache. The stable alternative it names is to route every call through one unchanging meta-tool, `call_tool({name, args})`, so the array never changes. Disconnecting a server is a conversation boundary, not a per-turn edit.

Dynamic server management is the same idea one level up: keep a registry of servers and short descriptions, connect only when the task needs that server, and drop it when it does not. The page also says a skill file may name the servers it needs. Skills are out of scope here.

Programmatic tool calling, also called code mode, is the second pattern. The host turns schemas into typed stubs. The model writes a script. A sandbox runs it, the host brokers each stub call to the right server, and only the script's final output returns to the model. The page says this requires a sandbox and that its runtime table is a set of examples, not an endorsement. Those runtimes are not catalogued in this pass.

Constraint, not a pick: the written acceptance bar is one client-side function that can list and invoke. That shape is the stable meta-tool, not "inject every tool." `list_only` is a coarse catalog. It is not the inspect step, and it is not code mode. Code mode is a separate host capability. Nothing in the acceptance bar requires it.

## Security frameworks for a local bridge

Three official documents. They apply to different layers. Mixing them up is how a local stdio host grows an OAuth stack it is not supposed to have.

### Authorization is for HTTP, not stdio

`https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization`

Authorization is optional. An HTTP transport should conform to the specification. An STDIO transport should not, and should retrieve credentials from the environment. Alternative transports must follow the security practice of that protocol.

Where the HTTP rules do apply, the security-considerations page requires RFC 8707 resource indicators on authorization and token requests, audience checks on the server, and a ban on token passthrough. A server must accept only tokens issued for itself. If it calls an upstream API, that call uses a separate token. The client's token is not forwarded. `https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations`

The 2026-07-28 security tutorial restates the ban. Token passthrough means accepting a client token that was not issued to the MCP server and forwarding it downstream. The tutorial says the authorization specification forbids it, and says servers must not accept tokens that were not explicitly issued for them. It also treats confused-deputy attacks as a required control for MCP proxy servers that connect to a third-party authorization server. `https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices`

A local bridge that later opens Streamable HTTP and forwards the caller's bearer token sits in that proxy class. This pass does not design that path. Enterprise-Managed Authorization is an extension for remote servers and an enterprise identity provider. It is not a stdio control.

### The stdio trust domain is the host's problem

`https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/local-server-security`

A local server is an ordinary child process. It inherits the user's environment and can read what that user can read. The protocol does not govern that. The guide's scope is a machine the operator controls, typically launched over stdio. Remote hardening is a different topic.

The stdio trust model, in the guide's words: the client and a stdio server share one trust domain. They run with the same privileges. Neither the protocol nor the SDKs defend one against the other, because launching the server is already code execution. The SDKs assume full trust between stdio peers. Isolation is the host's job and the operator's job, and it is decided before launch. The transport is not a sandbox. The trust domain is also cumulative: every configured server shares the model context, so one server can influence how the agent uses the others.

The principle the guide states: treat a third-party local server as untrusted code with exactly the privileges handed to it, and hand it as few as possible. Process isolation is called the highest-leverage mitigation. The baseline it names is a container, for example Docker or Podman, with no volume mounts beyond what the server needs. Stdio still works: the client talks to the container's stdin and stdout. Further steps on the same page (seccomp, an LSM, a microVM, a separate user, egress limits) are additional depth, not protocol requirements. The page also says pinning a launcher such as `npx` or `uvx` pins the top-level package only, while pinning an image digest freezes the tree. That is a supply-chain control, not a package to adopt.

The same guide names a separate failure class: local bridges that connect stdio clients to remote servers have had critical flaws triggered by connecting to a malicious endpoint. Recorded as a threat class. Not investigated here.

### Secondary control list

`https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html` (fetched 2026-10-15)

The cheat sheet cites the 2026-07-28 spec and the local-server guidance. It does not contradict them. Least privilege per server, scoped credentials, and no shared admin token. Sandbox local servers; a bare chroot is not a process sandbox. Use stdio so the local server is not a listening MCP endpoint, and do not pretend that stdio limits the child's files, network, or credentials. Never auto-approve tool calls. The sheet's consent wording points at the spec principle already cited: explicit user consent before any tool invocation, and the ability to deny it. Tool annotations stay untrusted. Sensitive or destructive calls need a human approval or an equivalent execution-time check.

## What these frameworks already say about this tree

Facts only, carried forward from the current-version pass. Not fixes.

- The registered surface is one function, `mcp_call`, with `server_label`, `tool_name`, `arguments`, and `list_only`. That is a host-shaped meta-tool. It does not speak `tools/list` or `tools/call`.
- The child protocol is one private JSON object on stdin and one JSON blob on stdout. The stdio framework requires newline-delimited JSON-RPC, protocol-only stdout, and no client-written JSON-RPC responses.
- `list_only` returns the configured registry, including `command`. The tool framework's list is the server's `tools/list` result, grouped by server, not the process argv.
- Invoke is one `subprocess.run` with `MCP_TIMEOUT` (default 20 seconds) and no retained child. The tools page says clients should implement timeouts. The stdio page's shutdown sequence is close-stdin, wait, then signal. A killed one-shot process can satisfy the timeout. It does not by itself satisfy the framing.
- Default bind is loopback. Invoke requires a bearer token when `TOOL_TOKEN` is non-empty. The schema endpoint is unauthenticated. Stdio children should take their own credentials from the environment. The HTTP OAuth specification is the wrong framework for those children. The invoke bearer token is the host's own gate, not a token to pass through.
- Docker already drops capabilities, runs read-only, and limits memory and pids. The local-server guide still treats isolation of each third-party command as a host decision made before launch. The current registry entry is a host command string, not an isolation policy.

## Not in this pass

- Named gateways, servers, libraries, and SDK comparisons.
- Which model should rank a catalog. The client guide names provider tool-search and small models only as examples of a retrieval strategy.
- Whether code mode, Streamable HTTP, elicitation, or resources belong in the acceptance bar.
- Enterprise-Managed Authorization and the OAuth client-registration catalog.
- Any draft newer than 2026-07-28.

## Constraints the later design has to respect

- This process is the host. One client per configured server. The host keeps the conversation, the consent decision, and the boundary between servers.
- A stdio peer is newline-delimited JSON-RPC. Stdout is protocol only. The client writes requests and notifications, not JSON-RPC responses, and shuts the child down by closing stdin and then terminating it.
- Listing is `tools/list` after an optional `server/discover`. Calling is `tools/call`. A tool error the model can read is `isError: true` on a complete result.
- One stable client-side function is a documented host shape. Injecting every schema is the pattern the client guide says to leave once the catalog is large, not the pattern a small registry is forbidden to use.
- Stdio credentials come from the environment. Do not apply the HTTP authorization specification to a stdio child. Do not pass the caller's token through to a child or an upstream API.
- The protocol will not sandbox the child. Isolation, if any, is outside the JSON-RPC session and is decided before launch.
- Servers in the wild still speak the handshake era. A single-era client misses the other era.
