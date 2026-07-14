# TraceListResponse

Response for `GET /v1/traces`.

---

## Shape

```json
{
  "traces": [TraceSummary],
  "total": 42,
  "metrics": {
    "total_cost_usd": 0.0,
    "tokens_generated": 0,
    "fail_rate": 0.08,
    "total_events": 150
  }
}
```

---

## Fields

| Field | Type | Description |
|---|---|---|
| `traces` | [`TraceSummary[]`](./trace-summary.md) | Page of trace summaries |
| `total` | `integer` | Total trace count for the org |
| `metrics` | `TraceMetrics \| null` | Org-wide aggregate metrics |

### TraceMetrics

| Field | Type | Description |
|---|---|---|
| `total_cost_usd` | `float` | Total cost across all spans |
| `tokens_generated` | `integer` | Total tokens consumed |
| `fail_rate` | `float \| null` | Error span ratio (0.0–1.0) |
| `total_events` | `integer` | Total span count |

See [TraceSummary](./trace-summary.md) for nested trace objects.
