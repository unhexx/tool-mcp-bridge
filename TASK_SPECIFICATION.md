# TASK_SPECIFICATION.md — tool-mcp-bridge

**Project:** tool-mcp-bridge
**Version Target:** 1.0
**Primary Goal:** Expose locally configured MCP servers as one client-side function on 127.0.0.1, with tests for list and stdio invoke.

## Business Objectives

- Bootstrap the Agentix loop in this repository
- Ship the first INVEST task with tests

## Scope

**In scope:** application code, tests, and docs for this repository
**Out of scope:** vendoring a copy of agentic_loop_template

## Success Criteria

- All INVEST tasks in `.agent/TODO.md` marked DONE with tests passing.
- Reviewer approves with `status=DONE` and clean git sync.

All loop output must use strict JSON handoffs per `HANDOFF_SCHEMA.md`.