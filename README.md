### OptiSchema
AI-powered PostgreSQL performance: watch real workload, pinpoint hot queries, generate executable fixes, validate in a sandbox, and apply with confidence.

### Local setup (Docker)
- Prereqs: Docker + Docker Compose

1) Start core stack (DB + API + UI)
```bash
docker compose up --build
```
- UI: http://localhost:3000
- API: http://localhost:8000/docs

2) Optional: Start isolated sandbox Postgres (for safe benchmarks)
```bash
# Simple
docker compose up -d postgres_sandbox

# Or with profile
# docker compose --profile sandbox up -d postgres_sandbox
```
- The backend connects to sandbox via `REPLICA_DATABASE_URL` (already set in compose)

3) Environment variables (AI)
- LLM provider: `LLM_PROVIDER=gemini` (default)
- Keys (read at runtime; do not hardcode): `GEMINI_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`
- Provide via `.env` or shell export before `docker compose up`

### Environment (.env) setup
1) Create an env file from the example
```bash
cp .env.example .env
```
2) Open `.env` and fill in your values (leave AI keys blank if you won’t use AI features):
```dotenv
# Database Configuration
DATABASE_URL=postgresql://optischema:optischema_pass@postgres:5432/optischema
POSTGRES_PASSWORD=optischema_pass
POSTGRES_DB=optischema
POSTGRES_USER=optischema

# OpenAI / Gemini / DeepSeek (optional)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o
GEMINI_API_KEY=
DEEPSEEK_API_KEY=
LLM_PROVIDER=gemini  # gemini | openai | deepseek

# WebSocket Configuration
UI_WS_URL=ws://localhost:8000/ws

# Backend Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_RELOAD=true

# Frontend Configuration
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=3000

# Development Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Cache Configuration
CACHE_TTL=3600
CACHE_SIZE=1000

# Analysis Configuration
POLLING_INTERVAL=30
TOP_QUERIES_LIMIT=10
ANALYSIS_INTERVAL=60

# Sandbox Configuration
SANDBOX_DATABASE_URL=postgresql://sandbox:sandbox_pass@postgres_sandbox:5432/sandbox
SANDBOX_POSTGRES_PASSWORD=sandbox_pass
SANDBOX_POSTGRES_DB=sandbox
SANDBOX_POSTGRES_USER=sandbox
REPLICA_DATABASE_URL=postgresql://sandbox:sandbox_pass@postgres_sandbox:5432/sandbox
REPLICA_ENABLED=true
```
3) Start services
```bash
docker compose up --build
```
Security note: never commit `.env` with real keys. Use placeholders in `.env.example` only.

### Feature guide
- Dashboard
  - Live hot queries (pg_stat_statements), KPI banners, latency trends
  - Filters, sorting, and query details panel
  - Data source badge: “Sampled”/“Replica” where applicable
- AI Suggestions
  - Explain-plan analysis → SQL patch (e.g., CREATE INDEX CONCURRENTLY) + rationale + risk
  - Cached responses; traceable suggestion metadata
- Sandbox Benchmark
  - Run EXPLAIN ANALYZE before/after in temp schema or read-replica
  - Shows Δ latency and Δ buffers; safe by default
- Apply / Rollback / Audit
  - Whitelisted DDL; rollback SQL generated; immutable audit trail
- Index Advisor
  - Suggests indexes for high-impact patterns; integrates with apply flow
- Connection Management
  - Postgres or RDS; read-only by default; enable pg_stat_statements helper

### How it works
1) Observe: rank queries via pg_stat_statements total_exec_time
2) Analyze: EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) + plan parser + heuristics
3) Suggest: rules + LLM propose safe patches with rationale and risk
4) Validate: sandbox benchmark for before/after deltas
5) Ship: apply with rollback and audit logging

### Local development (alt)
```bash
# Backend (FastAPI)
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (Next.js)
cd ../frontend
npm install
npm run dev
```

### Sandbox tips
- Default DB: container `optischema-sandbox` on 5433 (internal 5432)
- Compose profile: `docker compose --profile sandbox up -d postgres_sandbox`
- Backend auto-points to sandbox via `REPLICA_DATABASE_URL`

### Safety and privacy
- Read-only by default; least-privilege connection
- Whitelisted DDL only (… CONCURRENTLY, IF (NOT) EXISTS)
- PII-safe mode and cache controls available

### Troubleshooting
- If frontend can’t reach API, ensure `optischema-api` is healthy and `NEXT_PUBLIC_API_URL` points to it
- If no queries appear, verify pg_stat_statements enabled in your DB
- For AI-backed features, export a provider key (no hardcoding)