# TraceGraphResponse

React Flow graph data for `GET /v1/traces/{trace_id}/graph`.

---

## Shape

```json
{
  "nodes": [GraphNode],
  "edges": [GraphEdge]
}
```

---

## GraphNode

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Span ID (matches `span_id`) |
| `type` | `string` | `"agentNode"`, `"toolNode"`, or `"llmNode"` |
| `data` | `GraphNodeData` | Node display data |
| `position` | `{ x: float, y: float }` | Placeholder position (layout applied client-side) |

### GraphNodeData

Uses **camelCase** to match frontend TypeScript types.

| Field | Type | Description |
|---|---|---|
| `label` | `string` | Display label |
| `status` | `"ok" \| "error"` | Span status |
| `spanId` | `string` | Span identifier |
| `durationMs` | `integer` | Duration in milliseconds |
| `spanType` | `string` | Original span type |

---

## GraphEdge

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Edge identifier (`{source}-{target}`) |
| `source` | `string` | Parent span ID |
| `target` | `string` | Child span ID |
| `data` | `{ status: string } \| null` | Edge metadata (child span status) |

---

## Example

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
