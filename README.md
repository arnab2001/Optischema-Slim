<div align="center">
  <img src="frontend/public/image.png" alt="OptiSchema Logo" height="120">
  <p><strong>The Local-First Doctor for your PostgreSQL.</strong></p>

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
    <img src="https://img.shields.io/badge/WIP-Work%20InProgress-yellow" alt="Work in Progress">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Privacy-100%25-green" alt="Privacy">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Status-Private_Alpha-red" alt="Status">
  </a>
</div>

<!-- <img src="docs/screenshot.png" alt="OptiSchema Dashboard" width="100%" style="border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);"> -->


**🚧 We are currently finalizing the v1.0 Docker Image.**
Building from source works, but it requires manual config.

**[👉 Join the Waitlist](https://arnab2001.github.io/Optischema-Slim/)** to get the polished, zero-config Docker image when it drops.

## Why OptiSchema Slim?

*   **Privacy First**: Your schema and queries never leave localhost.
*   **Simulation Engine**: Verify index suggestions with HypoPG before touching production.
*   **Model Agnostic**: Use Ollama (SQLCoder) locally, or bring your own OpenAI/DeepSeek keys.

## Quick Start (30 Seconds)

```bash
# 1. Clone the repo
git clone https://github.com/arnab2001/Optischema-Slim.git

# 2. Run with Docker
docker-compose up -d

# 3. Open Dashboard
# http://localhost:8080
```

## Dev Setup (Separate FE/BE)

```bash
# Run backend + Vite dev server in separate containers
docker-compose -f docker-compose.dev.yml up --build

# Frontend (Vite) -> http://localhost:5173
# Backend (FastAPI) -> http://localhost:8080
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
