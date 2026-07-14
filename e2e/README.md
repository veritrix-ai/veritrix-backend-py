# End-to-end testing

Manual test harnesses for validating the full AgentOps pipeline locally:

```
Test agent (SDK)  →  Ingest API :8001  →  ClickHouse + Postgres
                                              ↓
                                    App API :8000  →  curl verification
```

No UI required.

## Prerequisites

1. **Docker** — databases running:

   ```bash
   cd backend
   docker compose up -d
   ```

2. **APIs** — two terminals:

   ```bash
   cd backend
   PYTHONPATH=. uvicorn ingest.main:app --port 8001 --reload
   PYTHONPATH=. uvicorn api.main:app --port 8000 --reload
   ```

3. **Python deps** (minimum):

   ```bash
   python3 -m pip install greenlet httpx pydantic python-dotenv
   cd backend && python3 -m pip install -e ".[dev]"
   ```

4. **Environment** (optional — defaults work for local dev):

   ```bash
   cp backend/e2e/.env.example backend/e2e/.env
   # edit OPENAI_API_KEY for customer-service and crewai tests
   ```

## Test suites

| Suite | Description | Quick run |
|---|---|---|
| [manual](./manual/README.md) | Minimal SDK spans (no OpenAI) | `./manual/validate.sh` |
| [customer-service](./customer-service/README.md) | OpenAI Agents multi-agent demo (from Colab) | `./customer-service/validate.sh` |
| [crewai](./crewai/README.md) | CrewAI two-agent crew (step_callback integration) | `./crewai/validate.sh` |

## Run everything

```bash
cd backend/e2e
chmod +x manual/run.sh manual/validate.sh customer-service/run.sh customer-service/validate.sh run-all.sh
./run-all.sh
```

`run-all.sh` runs the **manual** suite only (no OpenAI key needed). Run customer-service or crewai separately when you have `OPENAI_API_KEY` set.

## Demo credentials

| Item | Value |
|---|---|
| Ingest API key | `ao_live_7f3a9c2e1b8d4f6a5e0c9b2a1d8e7f6b60f6fec` |
| App API org_id | `11111111-1111-1111-1111-111111111111` |
| Ingest URL | `http://localhost:8001` |
| App API URL | `http://localhost:8000` |

## Troubleshooting

See [backend/README.md](../README.md#troubleshooting) for Postgres volume reset, ClickHouse auth, and greenlet install.
