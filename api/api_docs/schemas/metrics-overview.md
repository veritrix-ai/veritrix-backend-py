# MetricsOverviewData

Response for `GET /v1/metrics/overview`.

---

## Shape

```json
{
  "overview": { ... },
  "span_end_states": [ ... ],
  "span_end_states_distribution": { ... },
  "spans_per_trace": [ ... ],
  "trace_duration_distribution": [ ... ]
}
```

---

## overview (TraceMetrics)

| Field | Type | Description |
|---|---|---|
| `total_cost_usd` | `float` | Total cost across all spans |
| `tokens_generated` | `integer` | Total tokens consumed |
| `fail_rate` | `float \| null` | Error span ratio |
| `total_events` | `integer` | Total span count |
| `monthly_spans` | `integer` | Spans ingested this month |
| `monthly_span_limit` | `integer` | Plan limit (currently 5000) |

---

## span_end_states

Daily breakdown of span outcomes.

| Field | Type | Description |
|---|---|---|
| `date` | `string` | Date (`YYYY-MM-DD`) |
| `success` | `integer` | OK spans |
| `indeterminate` | `integer` | Indeterminate spans (currently 0) |
| `fail` | `integer` | Error spans |

---

## span_end_states_distribution

Org-wide totals.

| Field | Type | Description |
|---|---|---|
| `success` | `integer` | Total OK spans |
| `indeterminate` | `integer` | Total indeterminate spans |
| `fail` | `integer` | Total error spans |

---

## spans_per_trace / trace_duration_distribution

Histogram buckets for dashboard charts.

| Field | Type | Description |
|---|---|---|
| `label` | `string` | Bucket label (span count or duration ms) |
| `value` | `integer` | Number of traces in this bucket |
