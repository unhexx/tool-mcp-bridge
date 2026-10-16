# Models

Recorded 2026-10-16. This pass only. No brainstorm, no pick.

The process does not call a model. `src/` has no xAI client. The model is the caller of the one registered function. This note is the contract that caller publishes, and the model-side features that do not replace a stdio MCP client.

Sources are the xAI docs pages fetched the same day. Third-party model catalogs disagreed with each other on price and context. They are not used.

## The documented caller

`https://docs.x.ai/developers/models` (page dated 2026-09-21) lists Grok 4.7 as the flagship and says to use it for everything that is not audio, image, or video, including code. The model guide `https://docs.x.ai/developers/grok-4-7` and the model detail page `https://docs.x.ai/developers/models/grok-4.7` agree on the API name `grok-4.7`.

| Fact | Value | Page |
|---|---|---|
| API name | `grok-4.7` | model guide |
| Context | 500,000 tokens | model guide and detail page |
| Knowledge cutoff | May 2026 | model guide |
| Modalities | Text and image in, text out | model guide |
| Tools named on the guide | Function calling, web search, X search, code execution | model guide |
| Detail-page capabilities | Function calling, structured outputs, reasoning | model detail |
| Reasoning efforts | low, medium, high (default), xhigh | model guide |
| Input / output price on those pages | $2.00 / $6.00 per 1M tokens | model guide |
| Cached input on the detail page | $0.50 / 1M tokens | model detail |
| APIs | Responses and Chat Completions | model guide |

The detail page also shows us-east-1 rate limits (150 requests per second, 50,000,000 tokens per minute) and says the model is on more than one cluster, with a higher rate past 200k context. Those limits are cluster figures, not a property of this process.

Voice, image, and video models on the same models page are not function-calling callers for this function. Not listed further.

An older guide, `https://docs.x.ai/docs/guides/function-calling`, still says a maximum of 200 tools and creates the chat with `grok-4`. The current function-calling page (below) does not say 200 and its examples use `grok-4.7`. The 200 figure is not the current page.

## What the model sends this process

`https://docs.x.ai/developers/tools/function-calling`, last updated 2026-10-10. Examples use `grok-4.7`.

A client-side tool is a function definition: `name`, optional `description`, and `parameters`. The model does not run it. The request returns a call. The application runs it and sends the result back.

On the Responses API the call is an output item with `type: "function_call"`, `name`, `arguments` (a JSON string), and `call_id`. The result is an input item `type: "function_call_output"` with that `call_id` and a string `output`. The xAI SDK equivalent is a tool call on the chat response and `tool_result`. The facts pass already recorded the same split, including `get_tool_call_type(...) == "client_side_tool"`.

Schema rules on that page:

- `parameters` is required. The root must be a JSON Schema object (`"type": "object"`), or a root `anyOf` / `oneOf` whose every branch is an object. A scalar, an array, or a union with a non-object branch is rejected with HTTP 400 naming the tool.
- The schema table's `name` cell says the name is a unique identifier and that a request allows a maximum of 350 tools. The Responses reference says the same cap: a max of 350 tools, at `https://docs.x.ai/developers/rest-api-reference/inference/responses`.
- `description` may be omitted. The page says a clear description is what the model uses to decide.

`https://docs.x.ai/developers/model-capabilities/text/structured-outputs` says tool-call arguments are generated to match the tool's input schema, and that the strict flag is implicitly always true. It says Draft 2020-12 schemas work best and Draft-07 schemas are accepted. That is the same dialect the MCP tools page names as the default for `inputSchema`. The bridge does not have to re-validate for the model. The model has already emitted arguments that matched the function schema it was given. The child still has its own `inputSchema`. Those are two schemas. The function schema is the one the model saw (`server_label`, `tool_name`, `arguments`, `list_only`). The child schema is inside `arguments`.

Parallel function calling is on by default. One model response may contain several function calls. The page says to run them before the next model request. `parallel_tool_calls: false` turns that off. This HTTP invoke is one call. Parallelism is the application looping, not a batch method on this process.

`tool_choice` is `auto` (default), `required`, `none`, or one forced function. None of that is configured here. The model host sets it.

Built-in tools (web search, X search, code execution) run on xAI's side. A custom function pauses the request. Mixing both in one tools array is documented on the function-calling page. `max_turns` limits assistant turns inside one request, not the number of parallel calls in a turn, and a client-side call ends that request. The facts pass recorded the same `max_turns` rule. A follow-up that includes the function result starts a new count.

`https://docs.x.ai/developers/model-capabilities/text/best-practices` says to use the Responses API for reasoning models. Chat Completions has no field for encrypted reasoning, so a tool loop sent through it drops the earlier thinking. For `grok-4.7`, Responses always returns `reasoning.encrypted_content`, and the next request must send the reasoning items back unchanged along with the `function_call` items and then the `function_call_output`. That bookkeeping is in the model host. This process returns the function result and does not see the reasoning items.

The function name `mcp_call` collides with the Responses output type used for server-side MCP. The tool-usage page separates them by item type: `function_call` is local, `mcp_call` is server-side (`https://docs.x.ai/developers/tools/tool-usage-details`). A host that branches on the substring `mcp_call` instead of on `type` will mis-route. The name is a fact about the schema this package already serves. Renaming it is a design choice, not made here.

## Tool search is a model feature over declared functions

`https://docs.x.ai/cookbook/examples/progressive-tool-disclosure` is a Grok API recipe, not a second model. Mark functions `defer_loading: true` and add `toolSearch()`. The request still lists every tool name. The API omits the deferred definitions until search loads them. Search matches words, not meaning. The recipe says a loose query loads the wrong tool, and that the model can call a deferred tool it never loaded, guessing arguments from the name. The instructions in that recipe tell the model to search for the exact name with limit 1.

That mechanism only sees functions the application already put on the request. It does not connect to a stdio child, and it does not invent tools that were never declared. One registered function named `mcp_call` gives tool search nothing to rank. Expanding every child tool into the request is what would make `defer_loading` useful, and that expansion is solution C in the solutions note, which is not the one-function goal.

The MCP client guide's examples of a small ranking model (Haiku, Flash) are a host-built catalog. They are not xAI model ids, and this process does not host that catalog. Not compared here.

## What this does not change

- No model id belongs in this repository. List and stdio invoke do not need `grok-4.7`, an API key, or a tool-search call.
- The function the model sees stays a single JSON-Schema object with a name, a description, and object parameters. 350 is the documented request cap. One function is inside it. The cap matters only if a later design registers one function per child tool.
- The model repairs a bad child argument only if the function result text says what failed. A transport failure that never becomes `function_call_output` is invisible to the model. That split was already recorded.
- Remote MCP (`type: mcp` on the request, `mcp_call` in the output) is still a different path. The docs MCP server at `https://docs.x.ai/api/mcp` is a Streamable HTTP server for documentation. It is not a local stdio bridge and not a model.

## Not in this pass

- Which model should rank child tools, and whether to rename `mcp_call`.
- Aliases on the models page. The page says some exist. This pass did not copy the alias table.
- Benchmarks and third-party price tables.
- A design.
