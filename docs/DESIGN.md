# Дизайн: tool-mcp-bridge

## Назначение

Клиентский `mcp_call` к *локально* описанным MCP-серверам. Не xAI hosted MCP (`mcp_call` server-side).

## Границы

Сейчас: транспорт `stdio`, список серверов из `MCP_SERVERS` JSON, `list_only`, один вызов tool.

Не входит в MVP: произвольный MCP Streamable HTTP до появления теста, проброс в облако, discovery всей машины без allowlist.

## Архитектура

```
MCP_SERVERS=[{"label","transport","command"}]
invoke list_only -> реестр
invoke server_label+tool_name -> subprocess.run(command, input=JSON)
```

Контракт процесса-сервера (локальный упрощённый): stdin JSON `{tool, arguments}`, stdout JSON-результат.

Полный MCP JSON-RPC — отдельная задача, не ломать текущий echo-контракт без теста.

