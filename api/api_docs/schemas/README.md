# Schemas

Response models returned by the App API. Shapes match `frontend/lib/types.ts` and `backend/api/models.py`.

| Schema | Used by |
|---|---|
| [TraceListResponse](./trace-list.md) | `GET /v1/traces` |
| [TraceSummary](./trace-summary.md) | Nested in trace list |
| [TraceDetail](./trace-detail.md) | `GET /v1/traces/{trace_id}` |
| [Span](./span.md) | Nested in trace detail |
| [TraceGraphResponse](./trace-graph.md) | `GET /v1/traces/{trace_id}/graph` |
| [AgentListResponse](./agent-list.md) | `GET /v1/agents` |
| [MetricsOverviewData](./metrics-overview.md) | `GET /v1/metrics/overview` |
