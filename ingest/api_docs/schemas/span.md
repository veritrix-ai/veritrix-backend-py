# Span

OpenTelemetry-compatible span object. Each span represents one unit of work in an agent run (agent step, tool call, LLM call, or delegation).

---

## Shape

```json
{
  "trace_id": "string",
  "span_id": "string",
  "parent_span_id": "string | null",
  "name": "string",
  "start_time": "ISO 8601 datetime",
  "end_time": "ISO 8601 datetime | null",
  "status": "ok | error",
  "error_message": "string | null",
  "attributes": { },
  "input_preview": "string",
  "output_preview": "string"
}
```

---

## Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `trace_id` | `string` | Yes | Trace identifier shared by all spans in a run |
| `span_id` | `string` | Yes | Unique identifier for this span |
| `parent_span_id` | `string \| null` | No | Parent span ID for nested spans |
| `name` | `string` | Yes | Human-readable span name (e.g. agent role, tool name) |
| `start_time` | `datetime` | Yes | UTC start timestamp (ISO 8601) |
| `end_time` | `datetime \| null` | No | UTC end timestamp; defaults to `start_time` at insert time |
| `status` | `"ok" \| "error"` | No | Span outcome. Default: `"ok"` |
| `error_message` | `string \| null` | No | Error description when `status` is `"error"` |
| `attributes` | `object` | Yes | OTel attributes including required AgentOps keys |
| `input_preview` | `string` | No | First 500 characters of span input |
| `output_preview` | `string` | No | First 500 characters of span output |

---

## Required attributes

Every span's `attributes` object **must** include:

| Key | Type | Description |
|---|---|---|
| `agentops.agent_id` | `string` | Unique ID for the agent instance |
| `agentops.agent_name` | `string` | Human-readable agent name |
| `agentops.run_id` | `string` | Top-level trace / run ID |
| `agentops.framework` | `string` | `"langchain"`, `"crewai"`, or `"manual"` |
| `agentops.span_type` | `string` | `"agent"`, `"tool"`, `"llm"`, or `"delegation"` |

### Optional attributes

| Key | Type | Description |
|---|---|---|
| `agentops.duration_ms` | `integer` | Duration in milliseconds. Computed from timestamps if omitted |
| `agentops.tag` | `string` | Tag applied via SDK `default_tags` |
| `agentops.delegation` | `boolean` | Whether this step was a delegation (CrewAI) |

Additional custom attributes are allowed and stored as JSON in ClickHouse.

---

## Enumerations

### `status`

| Value | Description |
|---|---|
| `ok` | Span completed successfully |
| `error` | Span failed |

### `agentops.framework`

| Value | Description |
|---|---|
| `langchain` | Span from LangChain integration |
| `crewai` | Span from CrewAI integration |
| `manual` | Span from manual `agentops.trace()` calls |

### `agentops.span_type`

| Value | Description |
|---|---|
| `agent` | Agent step or chain execution |
| `tool` | Tool invocation |
| `llm` | Raw LLM call |
| `delegation` | Agent-to-agent delegation |

---

## Example — successful agent span

```json
{
  "trace_id": "abc123",
  "span_id": "span-001",
  "parent_span_id": null,
  "name": "Research Analyst",
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
    "agentops.duration_ms": 2500,
    "agentops.tag": "crewai"
  },
  "input_preview": "Analyze job market for ML engineers",
  "output_preview": "Found 3 trending roles in the current market..."
}
```

---

## Example — error tool span

```json
{
  "trace_id": "abc123",
  "span_id": "span-002",
  "parent_span_id": "span-001",
  "name": "web-search",
  "start_time": "2026-06-15T12:00:01.000Z",
  "end_time": "2026-06-15T12:00:01.800Z",
  "status": "error",
  "error_message": "Connection timeout after 800ms",
  "attributes": {
    "agentops.agent_id": "agent-001",
    "agentops.agent_name": "Research Analyst",
    "agentops.run_id": "abc123",
    "agentops.framework": "langchain",
    "agentops.span_type": "tool"
  },
  "input_preview": "ML engineer salary trends 2026",
  "output_preview": ""
}
```
