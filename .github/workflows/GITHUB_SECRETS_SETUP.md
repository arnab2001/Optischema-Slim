# GitHub Secrets Setup for GitHub Pages Deployment

## Required Secrets

To deploy the landing page to GitHub Pages, you need to add these secrets to your repository:

### Step 1: Go to Repository Settings

```
https://github.com/arnab2001/Optischema-Slim/settings/secrets/actions
```

### Step 2: Add These Secrets

Click **"New repository secret"** for each:

#### 1. SUPABASE_URL
- **Name:** `SUPABASE_URL`
- **Value:** `https://lnvkeysarmzdprtmufwt.supabase.co`
- **Description:** Your Supabase project URL

#### 2. SUPABASE_ANON_KEY
- **Name:** `SUPABASE_ANON_KEY`
- **Value:** `sb_publishable_WrIS4GLRZwLP8LJZi8TjfQ_cCPvoYZQ`
- **Description:** Your Supabase publishable/anonymous key

### Step 3: Verify Secrets Are Added

You should see both secrets listed:
- ✅ SUPABASE_URL
- ✅ SUPABASE_ANON_KEY

## What These Secrets Are Used For

The GitHub Actions workflows use these secrets during the build process to:
- Set environment variables for Next.js build
- Allow the waitlist form to connect to Supabase
- Keep your keys secure (not exposed in code)

## Security Notes

✅ **Safe to expose:** These are public/anonymous keys designed for frontend use  
✅ **Protected:** Secrets are encrypted and only available during workflow runs  
❌ **Never commit:** Never commit these values directly in code  

## After Adding Secrets

Once you add the secrets:
1. The workflows will automatically use them on the next push
2. Or trigger manually: Actions → Deploy GitHub Pages → Run workflow

## Troubleshooting

**Workflow fails with "Secret not found"**
- Make sure secret names match exactly: `SUPABASE_URL` and `SUPABASE_ANON_KEY`
- Check they're added under Actions secrets (not Dependabot or Codespaces)

**Build succeeds but waitlist doesn't work**
- Verify the keys are correct
- Check browser console for errors
- Ensure Supabase Edge Function is deployed
