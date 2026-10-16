# Задачи локальным агентам: tool-mcp-bridge

- [ ] T-001 Allowlist бинарей: `command[0]` только из `MCP_ALLOWED_BINS`.
- [ ] T-002 Таймаут и лимит stdout (уже timeout env; добавить обрезку и код ошибки).
- [ ] T-003 Адаптер JSON-RPC MCP (`tools/list`, `tools/call`) за флагом `MCP_PROTOCOL=jsonrpc|simple`.
- [ ] T-004 Фикстурный echo-сервер в `tests/fake_mcp.py`, не `python -c` в тесте как единственный образец.
- [ ] T-005 Запрет `transport=http` на не-loopback URL.
- [ ] T-006 Документировать, когда оставлять xAI `mcp(...)` server-side (удалённый SaaS MCP).

## Закрыто

- [x] T-000 list_only + stdio echo.

