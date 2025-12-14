#!/bin/bash
# Test the Supabase waitlist function directly

echo "Testing Supabase Waitlist Function..."
echo "URL: https://lnvkeysarmzdprtmufwt.supabase.co/functions/v1/waitlist"
echo ""

# Test with curl
curl -X POST https://lnvkeysarmzdprtmufwt.supabase.co/functions/v1/waitlist \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}' \
  -v

echo ""
echo ""
echo "If you see CORS errors, add your domain to Supabase CORS settings"
