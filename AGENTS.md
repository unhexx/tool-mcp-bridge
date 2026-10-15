# AGENTS.md — Instructions for Coding Agents

Full Agentix loop (O→C→T→D→R), template 3.13.0. `agentic_loop_template` is a symlink to the SSOT. Do not copy that tree into this repo.

## Project Goal

Expose locally configured MCP servers as one client-side function on 127.0.0.1, with tests for list and stdio invoke.

## Current Status

Bootstrap complete. First cycle has not started.

## Recommended Stack (do not deviate without an ADR)

- Language / runtime: Python 3.11+, setuptools, pytest, Docker Compose; loopback 127.0.0.1 only
- Stdio child client: `mcp>=2,<3` (`docs/adr/0001-mcp-sdk-stdio-client.md`). HTTP surface stays stdlib.
- Package manager: pip
- Tests: pytest -q
- Lint / types: python -m compileall -q src tests

## Exact Commands

```bash
python -m pip install -e ".[dev]"
python -m compileall -q src tests
pytest -q
TOOL_TOKEN=local TOOL_PORT=8096 python -m tool_mcp_bridge.server
```

## Definition of Done (any feature)

- [ ] Types / schemas updated at the single source of truth (no parallel interfaces)
- [ ] Tests for the change (fixture or unit); existing suite still green
- [ ] Docs / mapping table updated when the data shape changes
- [ ] No secrets, tokens, real user IDs, or raw PII committed
- [ ] One logical change per PR; conventional commit

## Boundaries — NEVER

- Commit `.env`, tokens, private keys, or live personal data
- Invent a second source of truth for types or domain objects
- Skip the exact commands above in favor of an improvised toolchain
- Mix unrelated concerns (parser + UI restyle, schema + drive-by refactors)

## Preferred Development Loop

If you use **Grok CLI**, run inside the project venv so `GROK_CLI_CHAT_PROXY_BASE_URL` points at the Agentix gateway (`http://127.0.0.1:8110/v1`). Do not send completions straight to the public chat-proxy. Opt out: `export AGENTIX_PROXY=0`.

1. Read this file, `TASK_SPECIFICATION.md`, `.agent/PLAN.md`, and `.agent/TODO.md`
2. Orchestrator uses `agentic_loop_template/prompts/short_orchestrator_prompt.md` and writes one JSON handoff
3. Smallest vertical slice that meets the next acceptance criterion
4. Write or update tests first when behavior changes
5. Run the exact lint + test commands
6. Commit as a human mid/senior developer (`agentic_loop_template/DEVELOPMENT_STANDARDS.md`)

Refresh the venv later with `bash Agent-Init.sh`.
