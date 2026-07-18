# AgentOps Backend

Backend services for the AgentOps observability platform.

## Services

| Service | Port | Purpose |
|---|---|---|
| Ingest API | 8001 | Receives spans from the Python SDK |
| App API | 8000 | Serves trace queries to the dashboard |

**Ingest API docs:** [`ingest/api_docs/README.md`](./ingest/api_docs/README.md)  
**App API docs:** [`api/api_docs/README.md`](./api/api_docs/README.md)

## Local development

### 1. Start databases

```bash
cd backend
docker compose up -d
```

This starts ClickHouse and PostgreSQL with seed data, including a development API key and demo org (`11111111-1111-1111-1111-111111111111`).

For an existing deployed PostgreSQL database, apply organization billing linkage once before
deploying the Clerk Billing frontend:

```bash
psql "$DATABASE_URL" -f scripts/add_clerk_org_id.sql
```

### 2. Configure environment

```bash
cp shared/.env.example shared/.env
```

### 3. Install dependencies

```bash
cd backend
pip install -e ".[dev]"
```

### 4. Run services

**Ingest API** (SDK writes):

```bash
cd backend
PYTHONPATH=. uvicorn ingest.main:app --host 0.0.0.0 --port 8001 --reload
```

**App API** (dashboard reads):

```bash
cd backend
PYTHONPATH=. uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Send a test span

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

### 6. Query traces from the App API

```bash
curl "http://localhost:8000/v1/traces?org_id=11111111-1111-1111-1111-111111111111"
curl "http://localhost:8000/v1/traces/trace-1"
curl "http://localhost:8000/v1/traces/trace-1/graph"
curl "http://localhost:8000/v1/agents?org_id=11111111-1111-1111-1111-111111111111"
curl "http://localhost:8000/v1/metrics/overview?org_id=11111111-1111-1111-1111-111111111111"
```

In local development without Clerk configured, the App API accepts requests without a session token and trusts the `org_id` query parameter.

## Tests

Unit tests:

```bash
cd backend
PYTHONPATH=. pytest ingest/tests/test_spans.py api/tests -q
```

Integration tests (requires docker-compose):

```bash
cd backend
AGENTOPS_RUN_INTEGRATION=1 PYTHONPATH=. pytest ingest/tests/test_spans_integration.py -q
```

## App API endpoints

```
GET /v1/traces?org_id=&limit=&offset=&status=
GET /v1/traces/{trace_id}
GET /v1/traces/{trace_id}/graph
GET /v1/agents?org_id=
GET /v1/metrics/overview?org_id=
```

All routes require `Authorization: Bearer {clerk_session_token}` in production. Validate with Clerk JWKS (`CLERK_JWKS_URL`).

## Ingest API contract

```
POST /v1/spans
Authorization: Bearer {api_key}

202 { "accepted": N }
401 { "error": "invalid api key" }
429 { "error": "rate limited" }
```

Spans are validated, accepted with `202`, and inserted into ClickHouse asynchronously in the background.

## End-to-end validation (no UI)

Validate the full pipeline with curl: **SDK → Ingest → ClickHouse → App API**.

### Prerequisites

1. Docker running: `docker compose up -d`
2. Ingest API on port 8001
3. App API on port 8000

```bash
# Terminal 1
cd backend && PYTHONPATH=. uvicorn ingest.main:app --port 8001 --reload

# Terminal 2
cd backend && PYTHONPATH=. uvicorn api.main:app --port 8000 --reload
```

E2E tests live under [`e2e/`](./e2e/README.md) with per-suite READMEs and run scripts.

### Option A — automated (manual suite, no OpenAI)

```bash
cd backend/e2e
chmod +x manual/validate.sh customer-service/validate.sh crewai/validate.sh run-all.sh
./manual/validate.sh
```

### Option B — OpenAI Agents (customer service / Colab demo)

```bash
pip install openai-agents python-dotenv
export OPENAI_API_KEY=your_key_here
cd backend/e2e/customer-service
./validate.sh
```

### Option C — CrewAI integration

```bash
pip install "crewai>=0.28.0" python-dotenv
export OPENAI_API_KEY=your_key_here
cd backend/e2e/crewai
./validate.sh
```

### Option D — manual steps

**1. Run the test agent (sends spans via SDK):**

```bash
cd backend/e2e/manual
./run.sh
```

**OpenAI Agents example (customer service multi-agent demo):**

```bash
cd backend/e2e/customer-service
./run.sh              # scripted demo
./run-interactive.sh  # interactive chat
```

**CrewAI example (two-agent sequential crew):**

```bash
cd backend/e2e/crewai
./run.sh
./run.sh --topic "multi-agent tracing"
```

Note the `trace_id` printed in the output.

**2. List traces:**

```bash
curl "http://localhost:8000/v1/traces?org_id=11111111-1111-1111-1111-111111111111"
```

**3. Get trace detail (replace TRACE_ID):**

```bash
curl "http://localhost:8000/v1/traces/TRACE_ID"
curl "http://localhost:8000/v1/traces/TRACE_ID/graph"
```

**4. Optional — ingest directly via curl (bypass SDK):**

```bash
curl -X POST http://localhost:8001/v1/spans \
  -H "Authorization: Bearer ao_live_7f3a9c2e1b8d4f6a5e0c9b2a1d8e7f6b60f6fec" \
  -H "Content-Type: application/json" \
  -d '{"spans":[...]}'
```

### Demo credentials (from seed data)

| Item | Value |
|---|---|
| API key (ingest) | `ao_live_7f3a9c2e1b8d4f6a5e0c9b2a1d8e7f6b60f6fec` |
| Org ID (app API) | `11111111-1111-1111-1111-111111111111` |

App API does not require auth in local dev when `CLERK_JWKS_URL` is unset.

## Troubleshooting

### APIs crash: `Router.__init__() got an unexpected keyword argument 'on_startup'`

Installing **crewai** (or other packages) in the same Python environment can upgrade **Starlette** to 1.x, which breaks **FastAPI 0.116**.

**Fix — pin Starlette back:**

```bash
pip install "starlette>=0.40.0,<0.48.0"
```

Then restart both uvicorn processes. For E2E agents (crewai, openai-agents), prefer a **separate venv** from the backend APIs.

### Postgres: Role "agentops" does not exist

The Postgres **data volume was created before** `POSTGRES_USER=agentops` was set. Postgres only applies env vars on first init — re-running `docker compose up` does not fix it.

Also check for an old orphan container `backend-db-1` holding the volume.

**Fix — reset the postgres volume:**

```bash
cd backend
chmod +x scripts/reset_postgres.sh
./scripts/reset_postgres.sh
```

Or manually:

```bash
cd backend
docker compose down --remove-orphans
docker volume rm backend_postgres_data
docker compose up -d
```

Then verify:

```bash
docker exec backend-postgres-1 psql -U agentops -d agentops -c "SELECT key_value FROM api_keys LIMIT 1;"
```

Restart the ingest API after resetting Postgres.

SQLAlchemy async requires the `greenlet` package:

```bash
pip install greenlet
# or reinstall backend deps
cd backend && pip install -e ".[dev]"
```

Restart the ingest API after installing.

### App API returns `500` / ClickHouse `403` or `Authentication failed`

ClickHouse on port 8123 must be reachable without auth issues.

**Option A — use Docker ClickHouse (recommended):**

```bash
cd backend
docker compose down
docker compose up -d
# wait ~10s for clickhouse-init
curl "http://localhost:8123/?query=SELECT%201"
```

**Option B — local ClickHouse with a password:**

Set in `backend/shared/.env`:

```bash
CLICKHOUSE_PASSWORD=your_password
```

Then restart both APIs.

Verify connectivity:

```bash
curl "http://localhost:8123/?query=SELECT%201"
```
