# TraceDetail

Full trace response for `GET /v1/traces/{trace_id}`.

---

## Shape

```json
{
  "trace_id": "abc123",
  "run_id": "abc123",
  "meta": { ... },
  "agents": [ ... ],
  "spans": [ ... ]
}
```

---

## Fields

| Field | Type | Description |
|---|---|---|
| `trace_id` | `string` | Trace identifier |
| `run_id` | `string` | Run identifier |
| `meta` | `TraceDetailMeta \| null` | Computed trace metadata |
| `agents` | `TraceAgentDetail[] \| null` | Derived agent breakdown |
| `spans` | [`Span[]`](./span.md) | All spans ordered by start time |

---

## TraceDetailMeta

| Field | Type | Description |
|---|---|---|
| `name` | `string` | Root agent / trace name |
| `version` | `string \| null` | SDK version (optional) |
| `model` | `string \| null` | Primary LLM model (optional) |
| `duration_ms` | `integer` | Total trace duration |
| `total_cost_usd` | `float \| null` | Total cost (optional) |
| `llm_calls` | `integer` | Count of LLM spans |
| `tool_calls` | `integer` | Count of tool spans |
| `errors` | `integer` | Count of error spans |
| `total_tokens` | `integer` | Total tokens (optional) |
| `tags` | `string[]` | Tags from span attributes |
| `start_time` | `string` | Trace start time (ISO 8601) |

---

## TraceAgentDetail

| Field | Type | Description |
|---|---|---|
| `name` | `string` | Agent name |
| `handoffs` | `string[]` | Delegation targets (future) |
| `tools` | `string[]` | Tool names used by this agent |

See [Span](./span.md) for span field definitions.
