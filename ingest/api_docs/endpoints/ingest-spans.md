# POST /v1/spans

Ingest a batch of OpenTelemetry-compatible spans from the AgentOps SDK or a custom client.

---

## Request

```
POST /v1/spans
Authorization: Bearer {api_key}
Content-Type: application/json
```

### Body

[`SpanBatch`](../schemas/span-batch.md)

```json
{
  "spans": [
    {
      "trace_id": "abc123",
      "span_id": "span-001",
      "parent_span_id": null,
      "name": "research-agent",
      "start_time": "2026-06-15T12:00:00.000Z",
      "end_time": "2026-06-15T12:00:02.500Z",
      "status": "ok",
      "error_message": null,
      "attributes": {
        "agentops.agent_id": "agent-001",
        "agentops.agent_name": "Research Analyst",
        "agentops.run_id": "abc123",
        "agentops.framework": "crewai",
        "agentops.span_type": "agent",
        "agentops.duration_ms": 2500
      },
      "input_preview": "Analyze job market for ML engineers",
      "output_preview": "Found 3 trending roles..."
    }
  ]
}
```

### Constraints

| Rule | Value |
|---|---|
| Min spans per batch | 1 |
| Max spans per batch | 500 |
| Required auth | Bearer API key |

See [Span schema](../schemas/span.md) for field definitions.

---

## Responses

### 202 Accepted

Batch validated and queued for async insert into ClickHouse.

[`AcceptedResponse`](../schemas/responses.md#acceptedresponse)

```json
{
  "accepted": 1
}
```

| Field | Type | Description |
|---|---|---|
| `accepted` | `integer` | Number of spans accepted in this batch |

---

### 401 Unauthorized

[Authentication error](../authentication.md#error-response)

```json
{
  "error": "invalid api key"
}
```

---

### 422 Unprocessable Entity

Request body failed schema validation. See [Errors](../errors.md).

---

### 429 Too Many Requests

[Rate limit exceeded](../errors.md#rate-limited)

```json
{
  "error": "rate limited"
}
```

---

## Processing behavior

1. **Validate** — API key, rate limit, batch size, and required span attributes.
2. **Respond** — Return `202` with `{ "accepted": N }` immediately.
3. **Insert** — Write spans to ClickHouse in a background task, tagged with the resolved `org_id`.

Spans are mapped to the ClickHouse `spans` table:

| ClickHouse column | Source |
|---|---|
| `trace_id` | `span.trace_id` |
| `span_id` | `span.span_id` |
| `parent_span_id` | `span.parent_span_id` |
| `agent_id` | `attributes.agentops.agent_id` |
| `agent_name` | `attributes.agentops.agent_name` |
| `run_id` | `attributes.agentops.run_id` |
| `framework` | `attributes.agentops.framework` |
| `span_type` | `attributes.agentops.span_type` |
| `start_time` | `span.start_time` |
| `end_time` | `span.end_time` (falls back to `start_time`) |
| `duration_ms` | `attributes.agentops.duration_ms` or computed from timestamps |
| `status` | `span.status` |
| `error_message` | `span.error_message` |
| `attributes` | Full `attributes` object as JSON string |
| `input_preview` | `span.input_preview` |
| `output_preview` | `span.output_preview` |
| `org_id` | Resolved from API key |

---

## Examples

### Successful ingest

```bash
curl -X POST http://localhost:8001/v1/spans \
  -H "Authorization: Bearer ao_live_7f3a9c2e1b8d4f6a5e0c9b2a1d8e7f6b60f6fec" \
  -H "Content-Type: application/json" \
  -d '{
    "spans": [{
      "trace_id": "trace-1",
      "span_id": "span-1",
      "name": "demo",
      "start_time": "2026-06-15T12:00:00Z",
      "end_time": "2026-06-15T12:00:01Z",
      "status": "ok",
      "attributes": {
        "agentops.agent_id": "agent-1",
        "agentops.agent_name": "Demo Agent",
        "agentops.run_id": "run-1",
        "agentops.framework": "manual",
        "agentops.span_type": "agent"
      }
    }]
  }'
```

### Error span

```json
{
  "spans": [{
    "trace_id": "trace-1",
    "span_id": "span-2",
    "name": "failing-tool",
    "start_time": "2026-06-15T12:00:00Z",
    "end_time": "2026-06-15T12:00:00.500Z",
    "status": "error",
    "error_message": "Tool execution timed out",
    "attributes": {
      "agentops.agent_id": "agent-1",
      "agentops.agent_name": "Demo Agent",
      "agentops.run_id": "run-1",
      "agentops.framework": "langchain",
      "agentops.span_type": "tool"
    },
    "input_preview": "{\"query\": \"SELECT * FROM users\"}",
    "output_preview": ""
  }]
}
```

### Nested spans (parent/child)

```json
{
  "spans": [
    {
      "trace_id": "trace-1",
      "span_id": "span-parent",
      "name": "crew-run",
      "start_time": "2026-06-15T12:00:00Z",
      "end_time": "2026-06-15T12:00:05Z",
      "status": "ok",
      "attributes": {
        "agentops.agent_id": "agent-1",
        "agentops.agent_name": "Orchestrator",
        "agentops.run_id": "trace-1",
        "agentops.framework": "crewai",
        "agentops.span_type": "agent"
      }
    },
    {
      "trace_id": "trace-1",
      "span_id": "span-child",
      "parent_span_id": "span-parent",
      "name": "llm-call",
      "start_time": "2026-06-15T12:00:01Z",
      "end_time": "2026-06-15T12:00:03Z",
      "status": "ok",
      "attributes": {
        "agentops.agent_id": "agent-1",
        "agentops.agent_name": "Orchestrator",
        "agentops.run_id": "trace-1",
        "agentops.framework": "crewai",
        "agentops.span_type": "llm"
      }
    }
  ]
}
```
