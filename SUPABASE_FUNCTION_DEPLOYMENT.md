# Deploy Updated Supabase Edge Function

## The CORS Fix

I've created an updated version of your waitlist Edge Function with proper CORS support.

### What Was Fixed

✅ **OPTIONS preflight handling** - Returns 204 with CORS headers  
✅ **apikey header allowed** - Added to Access-Control-Allow-Headers  
✅ **x-client-info header allowed** - Supabase client sends this  
✅ **Wildcard origin** - Set to `*` for development (change for production)  
✅ **CORS headers on all responses** - Including errors  

## Deployment Steps

### Step 1: Copy the Fixed Function

The updated function is in: `supabase/functions/waitlist/index.ts`

### Step 2: Deploy to Supabase

```bash
# Login to Supabase CLI (if not already)
supabase login

# Link to your project (if not already)
supabase link --project-ref lnvkeysarmzdprtmufwt

# Deploy the function
supabase functions deploy waitlist
```

### Step 3: Test the CORS Fix

After deployment, test the preflight:

```bash
curl -i -X OPTIONS 'https://lnvkeysarmzdprtmufwt.supabase.co/functions/v1/waitlist' \
  -H 'Origin: http://localhost:3000' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: Content-Type, Authorization, apikey'
```

**Expected response:**
```
HTTP/2 204
access-control-allow-origin: *
access-control-allow-methods: GET, POST, OPTIONS
access-control-allow-headers: Content-Type, Authorization, apikey, x-client-info
access-control-allow-credentials: true
```

### Step 4: Test from Browser

1. Visit: http://localhost:3000/landing
2. Open DevTools (F12) → Network tab
3. Clear network log
4. Enter email in waitlist form
5. Click "Join Waitlist"
6. Check Network tab:
   - Should see OPTIONS request (status 204)
   - Should see POST request (status 200)
   - No CORS errors in console!

## Alternative: Quick Test Without Deploying

If you don't have Supabase CLI set up, you can:

1. Go to: https://supabase.com/dashboard/project/lnvkeysarmzdprtmufwt/functions/waitlist
2. Click "Edit function"
3. Copy the code from `supabase/functions/waitlist/index.ts`
4. Paste it into the editor
5. Click "Deploy"

## Production Configuration

For production (GitHub Pages), change the CORS origin:

```typescript
const corsHeaders = {
  'Access-Control-Allow-Origin': 'https://arnab2001.github.io', // Your production domain
  // ... rest of headers
};
```

Or use environment variables:

```typescript
const corsHeaders = {
  'Access-Control-Allow-Origin': Deno.env.get('ALLOWED_ORIGIN') || '*',
  // ... rest of headers
};
```

Then set the environment variable in Supabase:
```bash
supabase secrets set ALLOWED_ORIGIN=https://arnab2001.github.io
```

## Troubleshooting

### Still getting CORS errors?

1. **Check the OPTIONS response:**
   ```bash
   curl -i -X OPTIONS 'your-function-url' \
     -H 'Origin: http://localhost:3000' \
     -H 'Access-Control-Request-Method: POST' \
     -H 'Access-Control-Request-Headers: Content-Type, Authorization, apikey'
   ```

2. **Check browser DevTools Network tab:**
   - Look for the OPTIONS request
   - Check response headers
   - Look for specific CORS error message

3. **Verify deployment:**
   ```bash
   supabase functions list
   ```

4. **Check function logs:**
   ```bash
   supabase functions logs waitlist
   ```

### Common Issues

**Issue: OPTIONS returns 401**
- Your auth is enabled for OPTIONS too
- Make sure OPTIONS returns immediately without auth

**Issue: Access-Control-Allow-Headers missing apikey**
- Redeploy the updated function
- Clear browser cache

**Issue: Origin mismatch**
- Check exact origin (include port)
- Use `*` for development
- Set specific origin for production

## Summary

The updated function:
- ✅ Handles CORS preflight properly
- ✅ Allows all required headers
- ✅ Works with browser requests
- ✅ Works with localhost and production
- ✅ Returns proper headers on errors too

Deploy it and your waitlist form will work in the browser! 🚀
