
### **Task 1: Database Schema** (1-1.5 days)
**Add tenant_id to all tables + constraints**

**New tables:**
```sql
-- tenants table
CREATE TABLE optischema.tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- tenant_connections (simplified, no encryption for now)
CREATE TABLE optischema.tenant_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES optischema.tenants(id),
    name TEXT NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    database_name TEXT NOT NULL,
    username TEXT NOT NULL,
    password TEXT NOT NULL, -- plaintext for now
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);
```

**Add tenant_id to existing tables:**
- `query_metrics` - add `tenant_id UUID NOT NULL REFERENCES optischema.tenants(id)`
- `analysis_results` - add `tenant_id UUID NOT NULL REFERENCES optischema.tenants(id)`
- `recommendations` - add `tenant_id UUID NOT NULL REFERENCES optischema.tenants(id)`
- `audit_logs` - add `tenant_id UUID NOT NULL REFERENCES optischema.tenants(id)`
- `index_recommendations` - add `tenant_id UUID NOT NULL REFERENCES optischema.tenants(id)`
- `benchmark_jobs` - add `tenant_id UUID NOT NULL REFERENCES optischema.tenants(id)`
- `connection_baselines` - add `tenant_id UUID NOT NULL REFERENCES optischema.tenants(id)`

**Constraints:**
- Composite unique indexes include `tenant_id`
- All FKs include `tenant_id` where applicable

### **Task 2: Tenant Context** (0.5-1 day)
**Extract tenant_id from requests and propagate through app**

**Changes:**
- Add `tenant_id` header to all API requests (frontend)
- Create tenant context middleware (backend)
- Update all service functions to accept `tenant_id` parameter
- Add tenant validation against `tenants` table

**Files to modify:**
- `frontend/lib/api.ts` - add tenant header
- `backend/main.py` - add tenant middleware
- All router files - extract tenant_id from request context
- All service classes - add tenant_id parameter

### **Task 3: Connection Manager** (1-1.5 days)
**Multi-tenant connection pools**

**Changes:**
- Replace single global pool with `{tenant_id: asyncpg.Pool}` mapping
- Add TTL and size limits for pool map
- Update all DB access to use tenant-specific pool
- Add tenant connection configuration management

**Files to modify:**
- `backend/connection_manager.py` - multi-tenant pool management
- All services that use DB - switch to tenant-specific pool
- `backend/config.py` - add tenant connection config

### **Task 4: Migrate File/SQLite Stores** (2-3 days)
**Replace all file/SQLite storage with Postgres + tenant_id**

**Sub-tasks:**
- **4a. Recommendations Store** (0.5 day)
  - Replace `SimpleRecommendationStore` with Postgres-backed service
  - Migrate existing `/tmp/simple_recommendations.json` data
  
- **4b. Audit Service** (0.5 day)
  - Replace SQLite with Postgres `audit_logs` table
  - Migrate existing `/tmp/optischema_audit.db` data
  
- **4c. Index Advisor** (0.75 day)
  - Replace SQLite with Postgres `index_recommendations` table
  - Migrate existing `/tmp/optischema_indexes.db` data
  
- **4d. Benchmark Jobs** (0.5 day)
  - Replace SQLite with Postgres `benchmark_jobs` table
  - Migrate existing data
  
- **4e. Connection Baselines** (0.5 day)
  - Replace SQLite with Postgres `connection_baselines` table
  - Migrate existing data

### **Task 5: Cache Strategy** (0.5-1 day)
**Move cache to Redis or Postgres with tenant scoping**

**Option A: Redis (Recommended)**
- Add Redis dependency and connection
- Update cache functions to use Redis with tenant-scoped keys
- Add Redis configuration

**Option B: Postgres Cache**
- Create `llm_cache` table with `tenant_id`
- Update cache functions to use Postgres
- Add cleanup job for expired entries

**Files to modify:**
- `backend/cache.py` - Redis or Postgres implementation
- `backend/analysis/llm.py` - update cache usage
- `backend/config.py` - add Redis config

### **Task 6: WebSocket Tenant Scoping** (0.5 day)
**Add tenant awareness to WebSocket connections**

**Changes:**
- Bind `connection_id -> tenant_id` on connect
- Filter broadcasts by tenant
- Update subscription management

**Files to modify:**
- `backend/websocket.py` - add tenant scoping
- `frontend` - include tenant_id in WebSocket messages

### **Task 7: Testing** (1-1.5 days)
**Multi-tenant smoke test and isolation verification**

**Tests:**
- Create two test tenants with separate data
- Verify API responses are tenant-scoped
- Test forced error scenarios (no cross-tenant data leakage)
- Test concurrent requests from different tenants
- Test WebSocket isolation

### **Task 8: Cleanup** (0.5 day)
**Remove file/SQLite artifacts**

**Changes:**
- Remove all `/tmp` file references
- Delete SQLite files
- Update documentation
- Clean up unused imports

## Time Estimates (Single Engineer)
- **Total: 6-9 days** (1.5-2 weeks)
- **With Redis**: +0.5 day for setup
- **Parallel work possible**: Tasks 4a-4e can be done in parallel

## Dependencies
1. Task 1 → Task 2, 3, 4 (schema must exist first)
2. Task 2 → Task 4, 6 (tenant context needed for services)
3. Task 3 → Task 4 (connection manager needed for DB access)
4. Task 4 → Task 7 (services must be migrated before testing)
5. Task 5, 6 can be done in parallel with Task 4

## Redis Decision
**Recommendation: Use Redis now** if you can spin it up easily. Benefits:
- Better performance than SQLite
- Built-in TTL/eviction
- Multi-instance shared cache
- Future-proof for scaling

**Fallback: Postgres cache** if Redis setup is complex - can migrate to Redis later.

Would you like me to start with Task 1 (Database Schema) or do you want to discuss any specific task in more detail?