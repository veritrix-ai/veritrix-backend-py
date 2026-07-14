# SpanBatch

Top-level request body for `POST /v1/spans`.

---

## Shape

```json
{
  "spans": [Span, ...]
}
```

---

## Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `spans` | `Span[]` | Yes | Array of spans to ingest |

---

## Validation rules

| Rule | Constraint |
|---|---|
| Minimum length | 1 span |
| Maximum length | 500 spans |

---

## Example

```json
{
  "spans": [
    {
      "trace_id": "abc123",
      "span_id": "span-001",
      "name": "research-agent",
      "start_time": "2026-06-15T12:00:00.000Z",
      "end_time": "2026-06-15T12:00:02.500Z",
      "status": "ok",
      "attributes": {
        "agentops.agent_id": "agent-001",
        "agentops.agent_name": "Research Analyst",
        "agentops.run_id": "abc123",
        "agentops.framework": "crewai",
        "agentops.span_type": "agent"
      }
    }
  ]
}
```

See [Span](./span.md) for individual span field definitions.
