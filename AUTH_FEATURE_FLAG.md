# Authentication Feature Flag - Quick Reference

## Toggle Authentication On/Off

### Environment Variable

```bash
# In .env file
ENABLE_AUTHENTICATION=false  # Development mode - no auth required
ENABLE_AUTHENTICATION=true   # Production mode - auth required
```

---

## Development Mode (Auth Disabled)

### Configuration
```bash
# .env
ENABLE_AUTHENTICATION=false
```

### Behavior
- ✅ All API endpoints accessible without authentication
- ✅ No JWT token required
- ✅ Auth endpoints (`/auth/login`, `/auth/register`) still work for testing
- ✅ Default user context automatically set:
  - `user_id`: "dev-user"
  - `tenant_id`: Default tenant ID from config
  - `email`: "dev@localhost"

### Startup Log
```
⚠️  Authentication DISABLED - All endpoints are public (development mode)
```

### Use Cases
- Local development
- Testing without auth overhead
- Quick prototyping
- CI/CD testing

---

## Production Mode (Auth Enabled)

### Configuration
```bash
# .env
ENABLE_AUTHENTICATION=true
JWT_SECRET=your-production-secret-key
JWT_EXPIRATION_HOURS=24
```

### Behavior
- 🔒 All API endpoints require valid JWT token
- 🔒 Requests without token return 401 Unauthorized
- 🔒 Token must be in `Authorization: Bearer <token>` header
- 🔒 Public endpoints still accessible: `/health`, `/docs`, `/auth/*`

### Startup Log
```
🔒 Authentication ENABLED - All endpoints require valid token
```

### Use Cases
- Production deployment
- Staging environment
- Security testing
- Multi-tenant production

---

## How to Use

### 1. Start with Auth Disabled (Development)

```bash
# .env
ENABLE_AUTHENTICATION=false

# Start backend
docker-compose up -d

# Make requests without auth
curl http://localhost:8080/api/metrics
# ✅ Works!
```

### 2. Test Auth Endpoints

```bash
# Register a user (works even with auth disabled)
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123",
    "name": "Test User"
  }'

# Response: { "access_token": "eyJ...", "token_type": "bearer" }

# Login
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123"
  }'
```

### 3. Enable Auth for Testing

```bash
# .env
ENABLE_AUTHENTICATION=true

# Restart backend
docker-compose restart optischema-api

# Now requests need auth
curl http://localhost:8080/api/metrics
# ❌ 401 Unauthorized

# With token
curl http://localhost:8080/api/metrics \
  -H "Authorization: Bearer eyJ..."
# ✅ Works!
```

### 4. Production Deployment

```bash
# .env.production
ENABLE_AUTHENTICATION=true
JWT_SECRET=<strong-random-secret>
JWT_EXPIRATION_HOURS=24

# Deploy
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Code Implementation

### Middleware Logic

```python
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Authentication middleware with feature flag."""
    
    # ⚡ FEATURE FLAG CHECK
    if not settings.enable_authentication:
        # Auth disabled - set default context and continue
        request.state.user_id = "dev-user"
        request.state.tenant_id = settings.default_tenant_id
        request.state.email = "dev@localhost"
        return await call_next(request)
    
    # Auth enabled - enforce authentication
    # ... token validation logic ...
```

### Accessing User Context

```python
from fastapi import Request

@router.get("/api/metrics")
async def get_metrics(request: Request):
    """Get metrics for current user."""
    
    # These are always available (from middleware)
    user_id = request.state.user_id
    tenant_id = request.state.tenant_id
    email = request.state.email
    
    # In dev mode: user_id = "dev-user"
    # In prod mode: user_id = actual user ID from token
```

---

## Testing Both Modes

### Test Script

```python
import asyncio
import httpx

async def test_auth_modes():
    """Test both auth modes."""
    
    base_url = "http://localhost:8080"
    
    # Test with auth disabled
    print("Testing with auth disabled...")
    response = await httpx.get(f"{base_url}/api/metrics")
    assert response.status_code == 200
    print("✅ No auth required")
    
    # Enable auth (change .env and restart)
    print("\nTesting with auth enabled...")
    
    # Register user
    response = await httpx.post(f"{base_url}/api/auth/register", json={
        "email": "test@example.com",
        "password": "SecurePass123",
        "name": "Test User"
    })
    token = response.json()['access_token']
    print("✅ User registered")
    
    # Try without token
    response = await httpx.get(f"{base_url}/api/metrics")
    assert response.status_code == 401
    print("✅ Auth required")
    
    # Try with token
    headers = {"Authorization": f"Bearer {token}"}
    response = await httpx.get(f"{base_url}/api/metrics", headers=headers)
    assert response.status_code == 200
    print("✅ Auth works")

asyncio.run(test_auth_modes())
```

---

## Troubleshooting

### Issue: Auth not disabled even with ENABLE_AUTHENTICATION=false

**Solution:**
1. Check `.env` file has correct value
2. Restart backend: `docker-compose restart optischema-api`
3. Check logs for startup message
4. Verify environment variable is loaded: `docker-compose exec optischema-api env | grep ENABLE_AUTHENTICATION`

### Issue: Getting 401 in development

**Solution:**
```bash
# Verify setting
docker-compose exec optischema-api python -c "from config import settings; print(settings.enable_authentication)"

# Should print: False

# If True, check .env file and restart
```

### Issue: Auth endpoints not working

**Solution:**
Auth endpoints (`/auth/login`, `/auth/register`) work regardless of feature flag setting. They're always public endpoints.

---

## Best Practices

### Development
```bash
# .env.development
ENABLE_AUTHENTICATION=false
```

### Staging
```bash
# .env.staging
ENABLE_AUTHENTICATION=true  # Test with auth
JWT_SECRET=staging-secret
```

### Production
```bash
# .env.production
ENABLE_AUTHENTICATION=true  # Always enabled
JWT_SECRET=<strong-random-secret>
```

---

## Migration Path

### Phase 1: Development (Week 1-2)
- `ENABLE_AUTHENTICATION=false`
- Build and test features without auth overhead
- Test auth endpoints separately

### Phase 2: Integration Testing (Week 3)
- `ENABLE_AUTHENTICATION=true`
- Test all features with auth enabled
- Fix any auth-related issues

### Phase 3: Staging (Week 4)
- `ENABLE_AUTHENTICATION=true`
- Full auth testing in staging environment
- Performance testing with auth

### Phase 4: Production (Week 5+)
- `ENABLE_AUTHENTICATION=true`
- Deploy with auth enabled
- Monitor and adjust

---

## Summary

**Key Points:**
- ✅ Single environment variable controls auth
- ✅ No code changes needed to toggle
- ✅ Safe for development (auth off)
- ✅ Secure for production (auth on)
- ✅ Auth endpoints always available for testing
- ✅ Easy to switch between modes

**Default:** `ENABLE_AUTHENTICATION=false` (safe for development)
**Production:** `ENABLE_AUTHENTICATION=true` (secure)
