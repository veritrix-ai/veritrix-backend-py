# GET /v1/traces/{trace_id}/graph

Returns nodes and edges for the React Flow agent graph visualization.

---

## Request

```
GET /v1/traces/{trace_id}/graph
Authorization: Bearer {clerk_session_token}
```

### Path parameters

| Parameter | Type | Description |
|---|---|---|
| `trace_id` | `string` | Trace identifier |

---

## Response

**Status:** `200 OK`

[`TraceGraphResponse`](../schemas/trace-graph.md)

```json
{
  "nodes": [
    {
      "id": "span-001",
      "type": "agentNode",
      "data": {
        "label": "Research Analyst",
        "status": "ok",
        "spanId": "span-001",
        "durationMs": 2500,
        "spanType": "agent"
      },
      "position": { "x": 0.0, "y": 0.0 }
    },
    {
      "id": "span-002",
      "type": "toolNode",
      "data": {
        "label": "web-search",
        "status": "ok",
        "spanId": "span-002",
        "durationMs": 800,
        "spanType": "tool"
      },
      "position": { "x": 0.0, "y": 0.0 }
    }
  ],
  "edges": [
    {
      "id": "span-001-span-002",
      "source": "span-001",
      "target": "span-002",
      "data": { "status": "ok" }
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

## Node type mapping

| `span_type` | React Flow node `type` |
|---|---|
| `agent` | `agentNode` |
| `tool` | `toolNode` |
| `llm` | `llmNode` |
| `delegation`, `other` | `agentNode` |

---

## Example

```bash
curl "http://localhost:8000/v1/traces/abc123/graph"
```

---

## Notes

- Node `position` values are placeholders (`0, 0`). The frontend applies dagre top-down layout via `layoutGraph()`.
- Edges are built from `parent_span_id` relationships.
- Edge stroke color is red when the child span has `status = "error"` (applied client-side).
- Graph node `data` fields use **camelCase** (`spanId`, `durationMs`, `spanType`) to match the frontend TypeScript types.
