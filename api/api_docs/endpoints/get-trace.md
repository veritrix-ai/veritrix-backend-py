# GET /v1/traces/{trace_id}

Returns full trace detail including all spans, computed metadata, and derived agent information.

---

## Request

```
GET /v1/traces/{trace_id}
Authorization: Bearer {clerk_session_token}
```

### Path parameters

| Parameter | Type | Description |
|---|---|---|
| `trace_id` | `string` | Trace identifier (matches `trace_id` / `run_id` from ingested spans) |

---

## Response

**Status:** `200 OK`

[`TraceDetail`](../schemas/trace-detail.md)

```json
{
  "trace_id": "abc123",
  "run_id": "abc123",
  "meta": {
    "name": "Research Analyst",
    "duration_ms": 2500,
    "llm_calls": 2,
    "tool_calls": 1,
    "errors": 0,
    "total_tokens": 0,
    "tags": ["crewai"],
    "start_time": "2026-06-15T12:00:00.000Z"
  },
  "agents": [
    {
      "name": "Research Analyst",
      "handoffs": [],
      "tools": ["web-search"]
    }
  ],
  "spans": [
    {
      "trace_id": "abc123",
      "span_id": "span-001",
      "parent_span_id": null,
      "agent_id": "agent-001",
      "agent_name": "Research Analyst",
      "run_id": "abc123",
      "framework": "crewai",
      "span_type": "agent",
      "start_time": "2026-06-15T12:00:00.000Z",
      "end_time": "2026-06-15T12:00:02.500Z",
      "duration_ms": 2500,
      "status": "ok",
      "error_message": null,
      "attributes": { "agentops.tag": "crewai" },
      "input_preview": "Analyze job market...",
      "output_preview": "Found 3 trending roles..."
    }
  ]
}
```

---

### 404 Not Found

```json
{
  "error": "trace not found"
}
```

---

## Example

```bash
curl "http://localhost:8000/v1/traces/abc123"
```

---

## Notes

- Spans are ordered by `start_time` ascending.
- `meta` is computed server-side from span data (duration, LLM/tool counts, errors).
- `agents` is derived from agent-type spans and their child tool spans.
- When Clerk auth is enabled, traces outside the user's org return `404`.
