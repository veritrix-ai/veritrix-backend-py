# AgentOps App API — Documentation

The App API serves read queries to the AgentOps dashboard. It reads span data from ClickHouse and returns traces, agent graphs, and metrics. It is separate from the Ingest API (port 8001) which receives spans from the SDK.

| | |
|---|---|
| **Base URL (local)** | `http://localhost:8000` |
| **Port** | `8000` |
| **Protocol** | HTTPS in production; HTTP for local development |
| **Content type** | `application/json` |
| **OpenAPI spec** | [`openapi.yaml`](./openapi.yaml) |
| **Interactive docs** | `http://localhost:8000/docs` (Swagger UI, when server is running) |
| **ReDoc** | `http://localhost:8000/redoc` (when server is running) |

---

## Documentation index

| Document | Description |
|---|---|
| [Authentication](./authentication.md) | Clerk session tokens, org scoping |
| [Endpoints](./endpoints/README.md) | All HTTP routes |
| [Schemas](./schemas/README.md) | Response body shapes |
| [Errors](./errors.md) | Status codes and error payloads |
| [OpenAPI](./openapi.yaml) | Machine-readable API specification |

---

## Quick start

### 1. Start the service

```bash
cd backend
docker compose up -d
cp shared/.env.example shared/.env
PYTHONPATH=. uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Ensure spans have been ingested via the [Ingest API](../ingest/api_docs/README.md) first.

### 2. List traces

```bash
curl "http://localhost:8000/v1/traces?org_id=11111111-1111-1111-1111-111111111111"
```

In local development without Clerk configured, no `Authorization` header is required and the `org_id` query parameter is trusted directly.

With Clerk configured in production:

```bash
curl "http://localhost:8000/v1/traces?org_id=YOUR_ORG_ID" \
  -H "Authorization: Bearer YOUR_CLERK_SESSION_TOKEN"
```

### 3. Get trace detail

```bash
curl "http://localhost:8000/v1/traces/trace-1"
```

### 4. Get trace graph

```bash
curl "http://localhost:8000/v1/traces/trace-1/graph"
```

---

## Dashboard integration

The Next.js dashboard calls this API through `frontend/lib/api.ts`:

| Frontend function | App API route |
|---|---|
| `getTraces()` | `GET /v1/traces` |
| `getTrace()` | `GET /v1/traces/{trace_id}` |
| `getTraceGraph()` | `GET /v1/traces/{trace_id}/graph` |
| `getAgents()` | `GET /v1/agents` |
| `getMetricsOverview()` | `GET /v1/metrics/overview` |

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local`.

---

## Architecture notes

- All list endpoints require an `org_id` query parameter scoped to the authenticated user's organization.
- Trace detail and graph endpoints resolve spans by `trace_id` and enforce org access when Clerk auth is enabled.
- Data is read from ClickHouse (`spans` table). User/org metadata comes from PostgreSQL.
- Graph node positions are returned as `{ x: 0, y: 0 }` — the frontend applies dagre layout client-side.

---

## Related

- [Backend README](../../README.md) — local development setup
- [Ingest API docs](../ingest/api_docs/README.md) — span ingestion
- [AGENTS.md](../../../AGENTS.md) — full platform architecture
