# How to Get the Correct Supabase Key

## ❌ The Problem

The key you provided is a "publishable" token:
```
sb_publishable_WrIS4GLRZwLP8LJZi8TjfQ_cCPvoYZQ
```

But we need the **anon/public JWT key** instead.

## ✅ Get the Correct Key

1. **Go to your Supabase Dashboard:**
   https://supabase.com/dashboard/project/lnvkeysarmzdprtmufwt/settings/api

2. **Look for the "Project API keys" section**

3. **Copy the key labeled "anon" or "public"**
   - It should start with: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - It's a LONG JWT token (several hundred characters)
   - Example format: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxudmtleXNhcm16ZHBydG11Znd0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE2OTQ1NDMyMDAsImV4cCI6MjAxMDExOTIwMH0...`

4. **The correct section looks like this:**
   ```
   Project API keys

   anon public
   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBh...
   [Reveal] [Copy]

   service_role secret
   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBh...
   [Reveal] [Copy]
   ```

   Copy the **top one** (anon public), NOT the service_role one!

## Once You Have It

Update `frontend/.env.local`:
```bash
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...your-actual-key
```

Then restart your dev server:
```bash
# Stop the server (Ctrl+C)
make dev-frontend
```

## Quick Test

Once you have the correct key, test it:
```bash
curl -X POST 'https://lnvkeysarmzdprtmufwt.supabase.co/functions/v1/waitlist' \
  -H 'Authorization: Bearer YOUR_ACTUAL_ANON_KEY' \
  -H 'apikey: YOUR_ACTUAL_ANON_KEY' \
  -H 'Content-Type: application/json' \
  --data '{"email":"test@example.com"}'
```

You should get a success response like:
```json
{
  "status": "ok",
  "email": "test@example.com",
  "confirmed": false,
  "token": "...",
  "emailSent": false
}
```
