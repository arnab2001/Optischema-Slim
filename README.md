<div align="center">
  <img src="frontend/public/image.png" alt="OptiSchema Logo" height="120">
  <p><strong>The Local-First Doctor for your PostgreSQL.</strong></p>
<br/> <a href="https://www.producthunt.com/products/optischema-slim?embed=true&amp;utm_source=badge-featured&amp;utm_medium=badge&amp;utm_campaign=badge-optischema-slim" target="_blank" rel="noopener noreferrer"><img alt="OptiSchema Slim - Local-first AI PostgreSQL tuning with 'what-if' indexes | Product Hunt" width="250" height="54" src="https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=1077195&amp;theme=neutral&amp;t=1770744233923"></a><br/>
  <a href="https://github.com/arnab2001/Optischema-Slim/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Docker-Ready-blue?logo=docker" alt="Docker">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Status-Alpha-orange" alt="Status">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Privacy-100%25-green" alt="Privacy">
  </a>
</div>


<!-- <img src="docs/screenshot.png" alt="OptiSchema Dashboard" width="100%" style="border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);"> -->

## 🎯 All-In-One Docker Image

OptiSchema Slim now ships as a **single ~390MB Docker image** containing both the UI and API.

**No separate frontend container. No Node.js runtime. One pull, one run.**

## Why OptiSchema Slim?

*   **Privacy First**: Your schema and queries never leave localhost.
*   **Simulation Engine**: Verify index suggestions with HypoPG before touching production.
*   **Model Agnostic**: Use Ollama (SQLCoder) locally, or bring your own OpenAI/Gemini/DeepSeek keys.
*   **All-In-One**: Single container, single port (8080), built-in static UI serving.

### 🚀 Quickstart Guide

**Option 1: The 10-Second Demo (Recommended)**
Run an auto-configured environment with a "bad database" to see OptiSchema's analysis in action.
```bash
# Clone the repo
git clone https://github.com/arnab2001/Optischema-Slim.git
cd Optischema-Slim

# Start the Demo
docker compose -f docker-compose.demo.yml up --build
```
*   **URL**: `http://localhost:8452`
*   **Scenario**: Pre-loaded with slow queries and missing indexes.

**Option 2: Run with Your Database**
Pull the official image and connect to your local Postgres.
```bash
# pulls ~390MB image
docker pull arnab2001/optischema-slim:latest

# run on port 8080
docker run -p 8080:8080 arnab2001/optischema-slim:latest
```
*   **URL**: `http://localhost:8080`
*   **Setup**: Enter your `postgres://` connection string in the UI.

## 🛠️ Development (Local Source Build)

```bash
# Backend (FastAPI)
make dev-backend

# Frontend (Next.js)
make dev-frontend
```

## Features

*   **Real-time Monitoring**: Heatmaps and latency tracking via `pg_stat_statements`.
*   **AI Analysis**: Context-aware suggestions using your schema and table stats.
*   **Cost Verification**: Compare EXPLAIN costs (Original vs. Virtual Index) side-by-side.

## Architecture

The system follows a **Collect → Analyze → Simulate** pipeline designed for distinct safety and performance guarantees:

*   **Frontend**: **Vite + React** with Tailwind UI & Recharts for real-time visualization.
*   **Backend**: **FastAPI** paired with AsyncPG for high-conformance, non-blocking I/O.
*   **Core Engine**:
    *   **Metric Collection**: Ingests `pg_stat_statements` to fingerprint and rank queries by Total Time and IO.
    *   **Context Engine**: Enriches queries with live schema definitions, indices, and table statistics (tuple counts, bloat).
    *   **AI Analysis**: Router sends sanitized context to the configure LLM (Local/Cloud) to synthesize optimization strategies.
    *   **HypoPG Simulation**: Creates *virtual indexes* in a transient session to verify `EXPLAIN` cost reductions before suggesting them.

## Configuration / LLM Setup

<details>
  <summary>Click to view Configuration Details</summary>

### Environment Setup

1.  Create a `.env` file from the example:
    ```bash
    cp .env.example .env
    ```

2.  **To use Ollama**:
    *   Install Ollama and pull the model: `ollama pull sqlcoder:7b`
    *   Set `LLM_PROVIDER=ollama` in your `.env`.
    *   Ensure OptiSchema can reach your host (typically `http://host.docker.internal:11434`).

3.  **To use Cloud Models**:
    *   Add your `OPENAI_API_KEY`, `GEMINI_API_KEY`, or `DEEPSEEK_API_KEY` to the `.env` file.
    *   Set `LLM_PROVIDER` accordingly (e.g., `openai`, `gemini`).

4.  **Auto-Connection (Optional)**:
    *   Set `DATABASE_URL=postgresql://user:pass@host:5432/db` to skip the connection screen on startup.

</details>

## Roadmap / Status

*   ✅ Core Metrics
*   ✅ HypoPG Integration
*   🚧 Health Scan (In Progress)
*   🚧 History Persistence

**Status**: We are currently optimizing the Docker image for the public release. [Join the Waitlist](https://arnab2001.github.io/Optischema-Slim/) to get the v1 image.

## Contributing

PRs are welcome! Please check out the [backend/services](backend/services) to see how we handle different components.

---

<div align="center">
  <sub>Built with ❤️ for the PostgreSQL Community</sub>
</div>
