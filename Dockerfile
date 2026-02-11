# --- Stage 1: Build Frontend (Vite) ---
FROM node:18-alpine AS frontend-builder
WORKDIR /app

# Enable legacy OpenSSL for compatibility if needed
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Install build dependencies
RUN apk add --no-cache libc6-compat python3 make g++

# Copy package files
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Set environment for production build
# Empty string means relative paths will be used for API calls
ENV VITE_API_URL=""

# Build static assets (generates 'dist' directory)
RUN npm run build

# --- Stage 2: Build Backend (Python Virtual Env) ---
FROM python:3.11-slim AS backend-builder
WORKDIR /app

# Install build tools
RUN apt-get update && apt-get install -y \
    gcc \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt .

# Create and populate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# --- Final Stage: All-In-One Production Image ---
FROM python:3.11-slim AS runner
WORKDIR /app

# Copy pre-compiled virtual environment
COPY --from=backend-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend application code
COPY backend/ .

# Copy static frontend files to 'static' directory
# FastAPI serves these via StaticFiles
COPY --from=frontend-builder /app/dist ./static

# Ensure data directory exists for SQLite persistence
RUN mkdir -p /app/data

# Production environment defaults
ENV DATABASE_PATH=/app/data/optischema.db
ENV ENVIRONMENT=production
ENV DEBUG=false
ENV BACKEND_HOST=0.0.0.0
ENV BACKEND_PORT=8080

EXPOSE 8080

# Health check (FastAPI health endpoint)
HEALTHCHECK --interval=30s --timeout=15s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health/check || exit 1

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
