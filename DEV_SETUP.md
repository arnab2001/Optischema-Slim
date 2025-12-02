# Development Setup Guide

## Quick Start for Single Instance Development

### Prerequisites

1. Docker and Docker Compose installed
2. `.env` file configured with necessary credentials

### Starting the Backend

```bash
# Start all services (single instance)
docker-compose up -d

# Or start specific services
docker-compose up -d postgres optischema-api

# View logs
docker-compose logs -f optischema-api
```

### Verifying the Setup

1. **Check Health**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Validate Database Schema** (optional)
   ```bash
   # Exec into the backend container
   docker-compose exec optischema-api python validate_schema.py
   ```

3. **Quick Code Validation** (before starting)
   ```bash
   # Run from backend directory
   python quick_validate.py
   ```

### Stopping the Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

---

## What Changed (Stateless Backend)

### ✅ No More In-Memory State
- Analysis results now stored in PostgreSQL
- Recommendations stored in PostgreSQL
- WebSocket connections are tenant-aware

### ✅ Single Instance Works Fine
- All changes are backward compatible
- No configuration changes needed for single instance
- Multi-instance support is available when needed

### ✅ Development Workflow
1. Make code changes
2. Restart backend: `docker-compose restart optischema-api`
3. Check logs: `docker-compose logs -f optischema-api`

---

## Environment Variables

Required in `.env` file:

```bash
# Database
DATABASE_URL=postgresql://optischema:optischema_pass@postgres:5432/optischema

# Optional: Replica database
REPLICA_DATABASE_URL=postgresql://optischema:optischema_pass@postgres:5432/optischema
REPLICA_ENABLED=true

# LLM Configuration
OPENAI_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_key_here
LLM_PROVIDER=gemini

# Backend Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_RELOAD=true
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

# Multi-tenancy (defaults are fine for dev)
DEFAULT_TENANT_ID=00000000-0000-0000-0000-000000000001
DEFAULT_TENANT_NAME=Default Tenant
```

---

## Common Issues & Solutions

### Issue: Backend won't start

**Solution:**
```bash
# Check logs
docker-compose logs optischema-api

# Rebuild if needed
docker-compose build optischema-api
docker-compose up -d optischema-api
```

### Issue: Database connection errors

**Solution:**
```bash
# Ensure postgres is healthy
docker-compose ps

# Check postgres logs
docker-compose logs postgres

# Restart postgres
docker-compose restart postgres
```

### Issue: Code changes not reflecting

**Solution:**
```bash
# Restart with rebuild
docker-compose up -d --build optischema-api

# Or force recreate
docker-compose up -d --force-recreate optischema-api
```

---

## Testing the Stateless Changes

### 1. Test Analysis Pipeline

```bash
# Trigger analysis
curl -X POST http://localhost:8000/api/analysis/run

# Get latest analysis
curl http://localhost:8000/api/analysis/latest

# Check status
curl http://localhost:8000/api/analysis/status
```

### 2. Test Recommendations

```bash
# Get recommendations
curl http://localhost:8000/api/suggestions/latest

# Get stats
curl http://localhost:8000/api/suggestions/stats
```

### 3. Test WebSocket (with tenant)

```javascript
// Connect with tenant_id
const ws = new WebSocket('ws://localhost:8000/ws?tenant_id=00000000-0000-0000-0000-000000000001');

ws.onmessage = (event) => {
  console.log('Received:', JSON.parse(event.data));
};

// Subscribe to updates
ws.send(JSON.stringify({
  type: 'subscribe',
  subscription_type: 'metrics'
}));
```

---

## Database Schema

### Verify Schema

```bash
# Run validation script
docker-compose exec optischema-api python validate_schema.py
```

### Manual Verification

```bash
# Connect to postgres
docker-compose exec postgres psql -U optischema -d optischema

# Check tables
\dt optischema.*

# Check tenant_id columns
SELECT table_name, column_name 
FROM information_schema.columns 
WHERE table_schema = 'optischema' 
AND column_name = 'tenant_id';
```

---

## Development Tips

### Hot Reload

The backend is configured with `--reload` flag, so code changes will automatically restart the server.

### Debugging

```bash
# View real-time logs
docker-compose logs -f optischema-api

# Exec into container
docker-compose exec optischema-api bash

# Run Python REPL
docker-compose exec optischema-api python
```

### Database Inspection

```bash
# View analysis results
docker-compose exec postgres psql -U optischema -d optischema -c "SELECT * FROM optischema.analysis_results ORDER BY created_at DESC LIMIT 5;"

# View recommendations
docker-compose exec postgres psql -U optischema -d optischema -c "SELECT id, title, recommendation_type FROM optischema.recommendations ORDER BY created_at DESC LIMIT 5;"
```

---

## Next Steps

1. ✅ **Start the backend** - `docker-compose up -d`
2. ✅ **Verify health** - `curl http://localhost:8000/health`
3. ✅ **Test endpoints** - Use the API to trigger analysis
4. ✅ **Check database** - Verify data is being stored
5. ⏳ **Production deployment** - When ready, deploy behind load balancer

---

## Multi-Instance (Future)

When you're ready to test multi-instance:

```bash
# Scale to 3 instances
docker-compose up -d --scale optischema-api=3

# Note: You'll need to configure a load balancer
# The code is already ready for this!
```

For now, single instance is perfect for development! 🚀
