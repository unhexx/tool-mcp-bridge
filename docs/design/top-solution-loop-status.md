# Top solution loop status

- updated: 2026-10-16
- pxpipe: ok (127.0.0.1:8100 and gateway 127.0.0.1:8110)
- phase: execute
- consensus: yes
- plan: finished
- design_doc: Reviewer consensus (`docs/design/tool-mcp-bridge-top-solution.md`), solution `function-over-sdk-stdio`
- execute_plan: finished. PR 1 `bb23a26`, PR 2 `9e40b51`, PR 3 `499f244`, all on `main`, not pushed. Every planned task is done. `compileall` quiet, `pytest -q` exit 0 (12 tests).
- writer_subagent_id: 01a141ab-81eb-7a00-99d3-8986f955b863 (consensus line only; do not resume)
- reviewer_subagent_id: 01a1419b-7fe2-76a3-943b-34d58ff4bcdd (re-review finished, 0 open; do not resume)
- design_scratch: `/tmp/grok-root/grok-design-doc-a0ac7c1d.md`
- summary_file: `/tmp/grok-root/grok-design-summary-a0ac7c1d.md`
- review_file: `/tmp/grok-root/grok-design-review-a0ac7c1d.md`
- review_copy: `docs/design/review-round-2.md` (matches `/tmp/grok-root/grok-design-review-a0ac7c1d.md`)
- review_round: 2
- open_issues: 0 (round 2 approve). Design doc records reviewer consensus on function-over-sdk-stdio.

## Deep research

| Question | Status | Artifact |
|---|---|---|
| current-version facts | done | `docs/design/research/01-current-version-facts.md` |
| frameworks | done | `docs/design/research/02-frameworks.md` |
| solutions | done | `docs/design/research/03-solutions.md` |
| open-source software | done | `docs/design/research/04-open-source.md` |
| models | done | `docs/design/research/05-models.md` |
| brainstorm | done | `docs/design/research/06-brainstorm.md` |

## PR plan

| PR | Status | Commit |
|---|---|---|
| PR 1 `build: depend on mcp>=2,<3 for the stdio child` | done | `bb23a26` on `main` (not pushed) |
| PR 2 `feat: speak MCP over stdio from mcp_call` | done | `9e40b51` on `main` (not pushed) |
| PR 3 `test: lock HTTP 200 for isError and HTTP 400 for mcp timeout` | done | `499f244` on `main` (not pushed) |

PR 3 file: `tests/test_tool.py` only. Real `make_handler(TOOL, SCHEMA, run)` on `ThreadingHTTPServer(("127.0.0.1", 0), ...)`. Wrapped `POST /v1/invoke` with bearer. `fail` on `modern_stdio.py` is HTTP 200, `ok` true, `tool` `mcp_call`, `result.isError` true, `result.resultType` `complete`, and the body has no `stderr` or `command` key. Silent child with `MCP_TIMEOUT=1` is HTTP 400 and `error` starts with `mcp timeout after 1s`. `src/tool_http.py` was not changed. Docker image was not rebuilt. `mem_limit` unchanged. No RSS measurement.

## This fire

Execute-plan slice PR 3 only. HTTP status lines are committed. Product check passed. The plan has no unfinished task.

## Next

Stop. Reviewer consensus is on `function-over-sdk-stdio` and every planned task is done.
