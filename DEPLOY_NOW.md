# 🚨 DEPLOY THE FUNCTION NOW!

## Why You're Getting 401

The **OLD** Edge Function is still running (without CORS support).
The **NEW** CORS-fixed function I created hasn't been deployed yet!

## ⚡ Quick Deploy (Via Dashboard - 2 Minutes)

### Step 1: Open Your Function Editor
```
https://supabase.com/dashboard/project/lnvkeysarmzdprtmufwt/functions/waitlist
```

### Step 2: Edit the Function

1. Click the **"..."** menu (three dots) in the top right
2. Click **"Edit function"** or **"Details"**
3. You'll see a code editor

### Step 3: Replace with New Code

1. **Select ALL the code** in the editor (Cmd+A / Ctrl+A)
2. **Delete it**
3. Open `supabase/functions/waitlist/index.ts` in your IDE (it's open now!)
4. **Copy ALL the code** (124 lines)
5. **Paste** into Supabase editor

### Step 4: Deploy

1. Click **"Deploy"** button (usually top right)
2. Wait ~10 seconds for deployment to complete
3. Look for success message

### Step 5: Test It!

**In your terminal:**
```bash
curl -i -X OPTIONS 'https://lnvkeysarmzdprtmufwt.supabase.co/functions/v1/waitlist' \
  -H 'Origin: http://localhost:3000' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: Content-Type, Authorization, apikey'
```

**Should see:**
```
HTTP/2 204
access-control-allow-headers: Content-Type, Authorization, apikey, x-client-info  ✅
```

**In your browser:**
1. Go to: http://localhost:3000/landing
2. Open DevTools (F12) → Network tab
3. Clear network log
4. Try the waitlist form
5. ✅ Should work now!

---

## 🔧 Alternative: Deploy via CLI

If you have Supabase CLI:

```bash
# Install (if not installed)
brew install supabase/tap/supabase

# Login
supabase login

# Link to project
supabase link --project-ref lnvkeysarmzdprtmufwt

# Deploy
supabase functions deploy waitlist
```

---

## ❓ Where's the Function Code?

It's in your repo at:
```
supabase/functions/waitlist/index.ts
```

Currently open in your IDE! Just copy it.

---

## What's Different in the New Code?

✅ Handles OPTIONS preflight requests  
✅ Returns CORS headers on all responses  
✅ Allows `apikey` header (the critical fix!)  
✅ Allows `x-client-info` header  
✅ Wildcard origin for development  

---

## 🎯 Summary

**Problem:** Old function → No CORS → Browser blocks request → 401 error  
**Solution:** Deploy new function → CORS enabled → Browser allows request → ✅ Success  

**Action:** Copy the code from `supabase/functions/waitlist/index.ts` and paste it into the Supabase dashboard editor, then click Deploy!

Takes 2 minutes and your waitlist will work! 🚀
