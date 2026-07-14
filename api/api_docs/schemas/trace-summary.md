# TraceSummary

Summary row for a single trace in the list view.

---

## Shape

```json
{
  "trace_id": "abc123",
  "run_id": "abc123",
  "agent_name": "Research Analyst",
  "name": "Research Analyst",
  "status": "ok",
  "duration_ms": 2500,
  "span_count": 5,
  "start_time": "2026-06-15T12:00:00.000Z",
  "tags": ["crewai"],
  "cost_usd": null,
  "error_count": 0
}
```

---

## Fields

| Field | Type | Description |
|---|---|---|
| `trace_id` | `string` | Trace identifier |
| `run_id` | `string` | Run identifier (usually same as `trace_id`) |
| `agent_name` | `string` | Primary agent name |
| `name` | `string \| null` | Display name (defaults to `agent_name`) |
| `status` | `"ok" \| "error"` | `"error"` if any span in the trace failed |
| `duration_ms` | `integer` | Total trace duration |
| `span_count` | `integer` | Number of spans in the trace |
| `start_time` | `string` | Earliest span start time (ISO 8601) |
| `tags` | `string[]` | Tags extracted from span attributes |
| `cost_usd` | `float \| null` | Total cost (optional, future) |
| `error_count` | `integer \| null` | Number of error spans |
