# OptiSchema — Product & Flow Overview

## What it does
AI-assisted PostgreSQL tuning: watch live workload (pg_stat_statements), surface hot queries, explain plans, propose fixes (LLM + rules), validate safely (sandbox/replica), and apply with rollback/audit safeguards.

## User journey (happy path)
1. Connect to a DB  
   - UI: `ConnectionWizard` / `connection-manager` components build a connection string (auto-SSL for RDS) and POST to `POST /api/connection/connect` (rewritten by `frontend/next.config.js` to the FastAPI backend).  
   - Backend: `connection_manager.connect()` creates an asyncpg pool, caches server version, and auto-enables pg_stat_statements when possible; connection details saved in SQLite via `storage.set_setting('active_connection', …)`.
2. Verify extensions  
   - UI prompts extension check; backend exposes `GET /api/connection/extension/check` and `POST /api/connection/extension/enable`.
3. See workload dashboard  
   - UI (`frontend/app/analytics/page.tsx`) fetches metrics (`/api/metrics/`) and vitals (`/api/metrics/vitals`) → renders `VitalsHeader`, `QueryGrid`, charts.  
   - Backend: `MetricService.fetch_query_metrics()` reads pg_stat_statements (version-aware columns) and returns sampled rows + total count; `fetch_vitals()` derives QPS, cache hit ratio, connection counts, WAL stats.
4. Inspect & analyze a query  
   - UI: clicking a row opens `InspectorSheet` (SQL, quick stats, Analyze button). Analyze posts to `/api/analysis/analyze`.  
   - Backend: analysis router runs EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON), parses via `analysis/explain.py` + heuristics in `analysis/core.py`; calls LLM (`analysis/llm.py`) for recommendations with simulation hooks.
5. Health scan  
   - UI: `HealthScanWidget` triggers `POST /api/health/scan`.  
   - Backend: `HealthScanService.perform_scan()` checks table bloat (`pg_stat_user_tables`), unused indexes (`pg_stat_user_indexes`), and config checks (`pg_settings`); results persisted in SQLite for `GET /api/health/latest`.
6. (Optional) Apply or sandbox-test fixes  
   - Apply/rollback routers manage safe DDL (CREATE INDEX CONCURRENTLY, rollback SQL) and audit logging; sandbox/replica URLs configured via `.env`.

## Additional user journeys & behaviors
- Switching connections: UI switcher posts to backend connect endpoints; current design keeps one active pool (new connections replace the old). Saved history is local unless extended server-side.  
- Metrics reset: `POST /api/metrics/reset` clears pg_stat_statements counters; dashboard reflects the new baseline.  
- Unsupported analysis: DDL/COPY and other non-EXPLAINable statements return an “unsupported” response; analyze SELECT-equivalents instead.  
- Health scan retrieval: after `POST /api/health/scan`, UI pulls `GET /api/health/latest` to render stored results; scans are rule-based, not AI-driven.

## Frontend flow (Next.js)
- App shell: `frontend/app/analytics/page.tsx`, `frontend/components/layout/app-shell.tsx`.
- Data access: direct fetches using `NEXT_PUBLIC_API_URL` (default `http://localhost:8080`) or via Next.js API routes (e.g., `/api/connection/test`) that forward headers/tenant info (`frontend/lib/apiMiddleware.ts`).
- State: `useConnectionStore` (Zustand) tracks connection status/string; `useAppStore` tracks theme/live mode/last updated. SWR is used selectively (`frontend/hooks/useMetrics.ts`).
- Routing and rewrites: `frontend/next.config.js` proxies `/api/*` to FastAPI (`optischema-api:8080` in Docker).
- Screens & key cards:
  - Connect (`frontend/app/page.tsx`): connection wizard (manual vs string), extension check gate before dashboard.
  - Dashboard (`frontend/app/analytics/page.tsx`):  
    - KPI row (`VitalsHeader`): QPS, Cache Hit Ratio, Active Connections with tooltips and connection utilization bar.  
    - Hot queries (`QueryGrid`): sortable columns (Calls, Mean, Total), IO dot (hit ratio), impact bar (% total time), click-through to Inspector.  
    - Inspector (`InspectorSheet`): SQL preview, quick stats (calls/mean/total), Analyze button; shows verification badge, reasoning, simulated costs, suggested SQL.  
    - DB info (`DbInfoPanel`): version, extensions, size, table counts, HypoPG/pg_stat_statements presence.  
    - Health (`HealthScanWidget`): trigger and display latest scan summary (bloat, unused indexes, config issues).  
    - Charts (`ChartsRow`): latency/throughput trends and heatmaps (Recharts-based components).  
  - Connection controls: `connection-wizard`, `connection-manager`, `DatabaseSwitcher` (status badge, test/switch/disconnect UI).
- Analysis actions: buttons call `/api/analysis/analyze` and render results with verification badges, suggested SQL, and simulated costs.
- UX guardrails: masks passwords in displayed connection strings, shows disabled/“—” states when metrics lack signal, tooltips for KPIs.

## Backend flow (FastAPI)
- Entry: `backend/main.py` registers routers (`metrics`, `analysis`, `connection`, `settings`, `health`) and CORS.
- Connection management: `connection_manager.py` owns a single asyncpg pool, caches server version, parses connection strings for display, and stores the active connection in SQLite via `storage.py`.
- Metrics: `services/metric_service.py`  
  - `_build_query_metrics_sql()` chooses version-correct pg_stat_statements columns (pre/post PG13) and filters system queries when requested.  
  - `fetch_query_metrics()` returns sampled metrics + total count.  
  - `fetch_vitals()` computes QPS (pg_stat_statements + tx fallback), cache hit ratio (suppressed if sample too small), active/max connections, WAL stats.  
  - `fetch_db_info()` returns version, extensions, sizes, and table stats.
- Analysis: `routers/analysis.py` (not shown here) calls `analysis/explain.py` for plan parsing, `analysis/core.py` for hot queries and metrics summary, and `analysis/llm.py` for LLM-backed recommendations with caching/failover (Gemini/OpenAI/DeepSeek configured via `.env`).
- Health scans: `services/health_scan_service.py` checks bloat (dead tuple ratio, vacuum recency), unused indexes (idx_scan=0), and config heuristics; results persisted for `/api/health/latest`.
- Storage: SQLite (`optischema.db`) via `storage.py` for settings, chat history, saved optimizations; recommendations have their own DB (`recommendations.db`).
- Safety: routers constrain DDL to safe forms; audit logging and rollback SQL exist in apply/rollback paths; CORS open in dev.

## Data paths (typical)
- Metrics: UI → `/api/metrics/` (proxied) → FastAPI → asyncpg → pg_stat_statements → JSON → UI render.
- Vitals: UI → `/api/metrics/vitals` → FastAPI → asyncpg → pg_stat_database/pg_stat_activity → UI render with status-aware display.
- Analysis: UI → `/api/analysis/analyze` (SQL) → FastAPI → EXPLAIN ANALYZE → plan parser + heuristics → optional LLM → suggestion returned to UI.
- Health scan: UI → `/api/health/scan` → FastAPI → bloat/config queries → result saved → UI fetches `/api/health/latest`.

## Configuration & environments
- Ports: UI 3000, API 8080, Postgres 5432 (sandbox 5433 internal).  
- Env: see `.env`/`README.md` — `NEXT_PUBLIC_API_URL`, `BACKEND_PORT`, database URLs, LLM keys/provider, replica/sandbox URLs.  
- Docker: `docker-compose.yml` spins up API, UI, Postgres; `docker-compose.sandbox.yml` adds sandbox.

## Nuances & current constraints
- Single active DB connection at a time; switching replaces the pool (per current code). Saved connection history is not yet persisted server-side.  
- Metrics fidelity depends on pg_stat_statements and uptime/reset windows; cache hit ratio is suppressed on tiny samples to avoid misleading 100%.  
- Some statements (e.g., COPY/DDL without EXPLAIN support) are not analyzable by the current `/api/analysis/analyze` flow.  
- AI is per-request for analysis; the health scan is rule-based, not an AI sweep.

## Where to look next
- Frontend: `frontend/app/analytics/page.tsx`, `frontend/components/**`  
- Backend: `backend/services/metric_service.py`, `backend/analysis/**`, `backend/services/health_scan_service.py`, `backend/connection_manager.py`, `backend/main.py`  
- Config: `.env`, `frontend/next.config.js`, `docker-compose.yml`, `docker-compose.sandbox.yml`
