# Waitlist Integration

## Overview

The landing page includes a waitlist signup form powered by a Supabase Edge Function.

## Supabase Edge Function

**Endpoint:** `https://lnvkeysarmzdprtmufwt.supabase.co/functions/v1/waitlist`

### Features
- Email validation
- Duplicate detection (upsert by email)
- Confirmation token generation
- Optional email provider integration

### Authentication

The Edge Function requires Supabase authentication. You need to include the anon key in requests:

**Option 1: Set environment variable (Recommended)**
```bash
# In frontend/.env.local
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
```

**Option 2: Make function public (Not recommended for production)**
Configure the Edge Function to allow anonymous access in Supabase dashboard.

### Request Format

```json
POST /functions/v1/waitlist
Content-Type: application/json

{
  "email": "user@example.com"
}
```

### Response Format

**Success (200):**
```json
{
  "status": "ok",
  "email": "user@example.com",
  "confirmed": false,
  "token": "uuid-token-here",  // only if no email provider configured
  "emailSent": false
}
```

**Error (400/500):**
```json
{
  "error": "Email is required"
}
```

## Database Schema

```sql
CREATE TABLE waitlist (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  confirm_token TEXT,
  confirmed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  confirmed_at TIMESTAMP
);
```

## Frontend Integration

### Location
- Landing page: `frontend/app/landing/page.tsx`
- API client: `frontend/lib/waitlist.ts`

### Component: WaitlistSection

The waitlist form includes:
- Email input with validation
- Loading states
- Success/error messages
- Disabled state after successful submission

### States
1. **Idle** - Ready to accept input
2. **Loading** - Submitting to API
3. **Success** - Email submitted successfully
4. **Error** - Failed to submit

## Email Provider Setup (Optional)

To send confirmation emails, set up an email provider in your Supabase Edge Function:

1. **Add environment variable:**
   ```bash
   MAIL_PROVIDER=sendgrid  # or your provider
   ```

2. **Configure provider in the Edge Function:**
   ```typescript
   // Add your email sending logic
   if (EMAIL_PROVIDER === 'sendgrid') {
     // Send email via SendGrid API
   }
   ```

### Recommended Providers
- **SendGrid** - Easy API integration
- **Resend** - Modern email API
- **AWS SES** - Cost-effective for high volume
- **Postmark** - Transactional emails

### Email Template Example

```html
Subject: Confirm your OptiSchema waitlist signup

Hi there!

Thanks for joining the OptiSchema waitlist. Click the link below to confirm:

https://arnab2001.github.io/Optischema-Slim/confirm?token={token}

Best,
The OptiSchema Team
```

## Testing

### Local Testing

1. **Start the dev server:**
   ```bash
   make dev-frontend
   ```

2. **Visit the landing page:**
   ```
   http://localhost:3000/landing
   ```

3. **Test the form:**
   - Enter an email
   - Click "Join Waitlist"
   - Check the response message

### Production Testing

Once deployed to GitHub Pages:
```
https://arnab2001.github.io/Optischema-Slim/
```

## Supabase Dashboard

### View Waitlist Entries

1. Go to: https://supabase.com/dashboard
2. Select your project
3. Navigate to Table Editor > waitlist

### SQL Queries

**Get all signups:**
```sql
SELECT * FROM waitlist ORDER BY created_at DESC;
```

**Get confirmed users:**
```sql
SELECT * FROM waitlist WHERE confirmed = true;
```

**Get unconfirmed users:**
```sql
SELECT * FROM waitlist WHERE confirmed = false;
```

**Count signups by date:**
```sql
SELECT DATE(created_at) as date, COUNT(*) as signups
FROM waitlist
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

## Customization

### Change Endpoint

Update in `frontend/lib/waitlist.ts`:
```typescript
const WAITLIST_ENDPOINT = 'your-new-endpoint'
```

### Customize UI

Edit the `WaitlistSection` component in `frontend/app/landing/page.tsx`:
- Change colors: Update Tailwind classes
- Modify copy: Edit text content
- Adjust layout: Modify flex/grid structure

### Add Fields

To collect more information (e.g., name, company):

1. **Update the Edge Function:**
   ```typescript
   const { email, name, company } = await req.json()
   ```

2. **Update the database schema:**
   ```sql
   ALTER TABLE waitlist ADD COLUMN name TEXT;
   ALTER TABLE waitlist ADD COLUMN company TEXT;
   ```

3. **Update the form component:**
   ```tsx
   <input name="name" placeholder="Your name" />
   <input name="company" placeholder="Company" />
   ```

## Security

- ✅ Email validation on client and server
- ✅ Rate limiting via Supabase (configured in project settings)
- ✅ Service role key protected (server-side only)
- ✅ CORS configured for your domain
- ✅ Input sanitization

## Monitoring

### Supabase Logs

View Edge Function logs:
```bash
supabase functions logs waitlist
```

### Analytics

Track waitlist signups:
- Total signups
- Conversion rate
- Time to confirm
- Dropoff points

## Troubleshooting

**Issue: "Method not allowed"**
- Ensure you're using POST method
- Check CORS settings in Supabase

**Issue: "Database error"**
- Check table exists: `waitlist`
- Verify column names match
- Check RLS policies

**Issue: Email not sending**
- Verify MAIL_PROVIDER is set
- Check email provider credentials
- Review Edge Function logs

**Issue: CORS errors**
- Add your domain to allowed origins in Supabase
- Check request headers

## Next Steps

1. **Set up email confirmation:**
   - Add email provider
   - Create confirmation page
   - Send welcome emails

2. **Add analytics:**
   - Track conversion rates
   - Monitor signup sources
   - A/B test messaging

3. **Enhance UX:**
   - Add social proof (e.g., "Join 1,234 others")
   - Show estimated launch date
   - Add referral program
