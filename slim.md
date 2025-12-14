# OptiSchema Slim Architecture

OptiSchema Slim is a local-first, zero-dependency PostgreSQL optimization tool designed for privacy and ease of use. This document outlines the core architecture, the "3-Tier Strategy" for optimization, and the key components implemented.

## Core Philosophy

1.  **Local-First**: Runs entirely on the user's machine (Docker). No data leaves the local environment.
2.  **Zero-Dependency**: No external databases (Redis, Postgres) required for the tool itself. Uses SQLite for internal state and `asyncpg` for direct target connections.
3.  **Simulation-First**: Prioritizes verifying changes (HypoPG) or estimating impact (Planner) before suggesting them.

## The 3-Tier Optimization Strategy

OptiSchema Slim employs a tiered approach to validate AI suggestions, ensuring safety and reliability.

### Tier 1: Verifiable (Index Suggestions)
*   **Trigger**: AI suggests adding an index.
*   **Mechanism**: Uses `HypoPG` (hypothetical indexes) to simulate the index without creating it.
*   **Validation**: Compares the query cost with and without the hypothetical index.
*   **Result**: "Verified" improvement percentage.

### Tier 2: Estimatable (Query Rewrites)
*   **Trigger**: AI suggests rewriting the SQL query.
*   **Mechanism**: Uses a "Safe Rewrite" sandbox.
    1.  Parses SQL with `sqlglot` to ensure it is a read-only `SELECT`.
    2.  Runs `EXPLAIN (FORMAT JSON)` on the *rewritten* query inside a transaction that is immediately rolled back.
    3.  **Crucial**: Does NOT use `ANALYZE`, so the query is never actually executed, preventing long-running load or side effects.
*   **Validation**: Compares the planner's cost estimate of the original vs. rewritten query.
*   **Result**: "Estimated" cost reduction.

### Tier 3: Advisory (Configuration/Schema)
*   **Trigger**: AI suggests configuration changes (e.g., `work_mem`) or schema refactoring.
*   **Mechanism**: N/A (Cannot be easily simulated safely).
*   **Validation**: Relies on the user's judgment.
*   **Result**: "Advisory" note.

## Rich Context Injection

To enable high-quality AI analysis, we inject detailed context into the LLM prompt.

1.  **Query Context**: The raw SQL query.
2.  **Execution Plan**: The `EXPLAIN` output (Total Cost, Node types) to understand *how* the DB executes it.
3.  **Schema Context**:
    *   **Table Stats**: Row counts (from `pg_class.reltuples`) to distinguish small vs. huge tables.
    *   **Columns**: Names and data types.
    *   **Existing Indexes**: Definitions from `pg_indexes` to avoid duplicate suggestions.

## Component Architecture

### 1. Connection Manager (`backend/connection_manager.py`)
*   **Role**: Manages the single active connection to the user's target PostgreSQL database.
*   **Implementation**: Uses `asyncpg` connection pool. Persists the connection string in SQLite so it survives restarts.

### 2. Storage Layer (`backend/storage.py`)
*   **Role**: Internal persistence for the tool.
*   **Implementation**: `aiosqlite` (SQLite). Stores:
    *   `settings` (Active connection string, preferences).
    *   `chat_history` (Past AI interactions).
    *   `saved_optimizations` (User-saved snippets).

### 3. Services Layer (`backend/services/`)
*   **`AnalysisOrchestrator`**: The "Brain". Coordinates the flow:
    1.  Calls `SchemaService` & `MetricService` to gather context.
    2.  Calls `LLMService` to get a suggestion.
    3.  Routes the suggestion to `SimulationService` based on the category (Index/Rewrite).
*   **`LLMService`**: Handles interaction with LLM providers (Ollama, OpenAI). Builds the "Rich Context" prompt.
*   **`SimulationService`**:
    *   `simulate_index`: Uses HypoPG.
    *   `simulate_rewrite`: Uses `EXPLAIN` (no ANALYZE) + `sqlglot` safety check.
*   **`SchemaService`**: Fetches table metadata (columns, indexes, row counts).
*   **`MetricService`**: Fetches query performance metrics from `pg_stat_statements`.

### 4. API Layer (`backend/routers/`)
*   **`analysis.py`**: Endpoints for `analyze` (Orchestrator) and `explain`.
*   **`metrics.py`**: Endpoints for viewing `pg_stat_statements` data.
*   **`connection.py`**: Endpoints for connecting/disconnecting.

## Data Flow

1.  **User** submits a query for analysis.
2.  **AnalysisRouter** calls **AnalysisOrchestrator**.
3.  **Orchestrator** gathers:
    *   `SchemaService`: "Table 'users' has 1M rows, index on 'id'".
    *   `DB`: Current EXPLAIN plan (Cost: 1000).
4.  **Orchestrator** sends context to **LLMService**.
5.  **LLM** responds: "Create index on 'email'".
6.  **Orchestrator** sees "INDEX" category -> calls **SimulationService.simulate_index**.
7.  **SimulationService** runs HypoPG -> New Cost: 50.
8.  **Orchestrator** returns result: "Verified 95% improvement".
