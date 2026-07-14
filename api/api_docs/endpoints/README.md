# Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| [`GET /health`](./health.md) | `/health` | No | Service health check |
| [`GET /v1/traces`](./list-traces.md) | `/v1/traces` | Yes | List traces for an org |
| [`GET /v1/traces/{trace_id}`](./get-trace.md) | `/v1/traces/{trace_id}` | Yes | Full trace with spans |
| [`GET /v1/traces/{trace_id}/graph`](./get-trace-graph.md) | `/v1/traces/{trace_id}/graph` | Yes | React Flow graph data |
| [`GET /v1/agents`](./list-agents.md) | `/v1/agents` | Yes | Agent health summary |
| [`GET /v1/metrics/overview`](./metrics-overview.md) | `/v1/metrics/overview` | Yes | Metrics dashboard data |

**Base URL:** `http://localhost:8000` (local development)

All authenticated endpoints accept Clerk session tokens. In local dev without Clerk, `org_id` query param is trusted directly.
