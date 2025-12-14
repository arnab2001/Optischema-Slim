# Waitlist Setup Guide

## Quick Fix for "Missing authorization header" Error

Your Edge Function requires authentication. Here's how to fix it:

## Step 1: Get Your Supabase Anon Key

1. Go to your Supabase dashboard: https://supabase.com/dashboard
2. Select your project
3. Go to **Settings** → **API**
4. Copy the **anon/public** key (NOT the service_role key!)

## Step 2: Add the Key to Your Environment

### For Local Development

Create `frontend/.env.local`:
```bash
NEXT_PUBLIC_SUPABASE_URL=https://lnvkeysarmzdprtmufwt.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...your-key-here
```

### For GitHub Pages (Production)

You have two options:

#### Option A: Hardcode in Build (Simple, but less secure)

Update the fetch call in `frontend/app/landing/page.tsx`:
```typescript
const response = await fetch('https://lnvkeysarmzdprtmufwt.supabase.co/functions/v1/waitlist', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_ANON_KEY_HERE',
  },
  body: JSON.stringify({ email: email.trim() }),
})
```

#### Option B: Use GitHub Secrets (More secure)

1. Add secret to GitHub repo:
   - Go to: https://github.com/arnab2001/Optischema-Slim/settings/secrets/actions
   - Click "New repository secret"
   - Name: `SUPABASE_ANON_KEY`
   - Value: Your anon key
   - Click "Add secret"

2. Update GitHub Actions workflow (`.github/workflows/deploy-pages.yml`):
```yaml
- name: Build landing page
  env:
    NEXT_PUBLIC_SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
  run: |
    cd frontend
    EXPORT_MODE=true npm run build
```

## Step 3: Alternative - Make Function Public (Easier, but check security)

If you want to allow public access without auth headers:

### Update Your Edge Function

Add this at the top of your Edge Function:
```typescript
// Handle CORS preflight
if (req.method === 'OPTIONS') {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}

// Continue with existing code...
```

And update the final response to include CORS headers:
```typescript
return new Response(JSON.stringify(resp), {
  status: 200,
  headers: {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
  }
});
```

Then deploy the updated function:
```bash
supabase functions deploy waitlist
```

## Step 4: Test It

### Test with curl (with auth):
```bash
curl -X POST https://lnvkeysarmzdprtmufwt.supabase.co/functions/v1/waitlist \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -d '{"email":"test@example.com"}'
```

### Test in browser:
1. Visit: http://localhost:3000/landing
2. Open browser console (F12)
3. Enter your email
4. Click "Join Waitlist"
5. Check console for logs

## Security Notes

### ✅ Safe to expose in frontend:
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` (anon/public key)

### ❌ NEVER expose in frontend:
- `SUPABASE_SERVICE_ROLE_KEY`
- Database passwords
- Private API keys

The anon key is designed to be public and has Row Level Security (RLS) policies that protect your data.

## Troubleshooting

### Still getting 401 errors?

1. **Check the key is correct:**
   ```bash
   echo $NEXT_PUBLIC_SUPABASE_ANON_KEY
   ```

2. **Restart dev server:**
   ```bash
   # Stop the server (Ctrl+C)
   make dev-frontend
   ```

3. **Check environment in code:**
   ```typescript
   console.log('Anon key present:', !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY)
   ```

### Getting CORS errors?

1. **Enable CORS in Supabase:**
   - Go to Settings → API
   - Add your domain to allowed origins:
     - `http://localhost:3000`
     - `https://arnab2001.github.io`

2. **Or update Edge Function** (see Step 3 above)

### Key not loading in production?

Make sure you're using `NEXT_PUBLIC_` prefix - Next.js only exposes env vars with this prefix to the browser.

## What's Next?

Once this is working:
1. ✅ Test locally: http://localhost:3000/landing
2. ✅ Commit changes
3. ✅ Push to GitHub
4. ✅ Deploy to GitHub Pages
5. ✅ Test on production: https://arnab2001.github.io/Optischema-Slim/

Need help? Check the browser console for detailed error logs.
