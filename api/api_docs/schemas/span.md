# Span

Individual span within a trace. Returned as part of [`TraceDetail`](./trace-detail.md).

---

## Shape

```json
{
  "trace_id": "string",
  "span_id": "string",
  "parent_span_id": "string | null",
  "agent_id": "string",
  "agent_name": "string",
  "run_id": "string",
  "framework": "langchain | crewai | manual | openai",
  "span_type": "agent | tool | llm | delegation | other",
  "start_time": "ISO 8601",
  "end_time": "ISO 8601",
  "duration_ms": 0,
  "status": "ok | error",
  "error_message": "string | null",
  "attributes": {},
  "input_preview": "string",
  "output_preview": "string",
  "model": "string | null",
  "prompt_tokens": 0,
  "completion_tokens": 0,
  "total_tokens": 0,
  "cost_usd": 0.0
}
```

---

## Fields

| Field | Type | Description |
|---|---|---|
| `trace_id` | `string` | Trace this span belongs to |
| `span_id` | `string` | Unique span identifier |
| `parent_span_id` | `string \| null` | Parent span for nesting |
| `agent_id` | `string` | Agent instance ID |
| `agent_name` | `string` | Human-readable agent name |
| `run_id` | `string` | Top-level run ID |
| `framework` | `string` | Source framework |
| `span_type` | `string` | Span category |
| `start_time` | `string` | UTC start (ISO 8601) |
| `end_time` | `string` | UTC end (ISO 8601) |
| `duration_ms` | `integer` | Duration in milliseconds |
| `status` | `string` | `"ok"` or `"error"` |
| `error_message` | `string \| null` | Error description |
| `attributes` | `object` | Full OTel attributes JSON |
| `input_preview` | `string` | First 500 chars of input |
| `output_preview` | `string` | First 500 chars of output |
| `model` | `string \| null` | LLM model name (optional) |
| `prompt_tokens` | `integer \| null` | Input tokens (optional) |
| `completion_tokens` | `integer \| null` | Output tokens (optional) |
| `total_tokens` | `integer \| null` | Total tokens (optional) |
| `cost_usd` | `float \| null` | Cost in USD (optional) |

Token and cost fields are reserved for future enrichment; currently `null` or `0` for SDK-ingested spans.
