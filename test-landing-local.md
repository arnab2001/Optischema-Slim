# Testing Landing Page Locally

## Quick Test

1. Start the frontend dev server:
   ```bash
   make dev-frontend
   ```

2. Open your browser and visit:
   ```
   http://localhost:3000/landing
   ```

3. You should see the OptiSchema Slim landing page with:
   - Hero section with "PostgreSQL Performance, Simplified"
   - Features grid
   - "How It Works" section
   - Quick start guide
   - CTA and footer

## What Works Now

✅ Landing page accessible at `/landing` route (not at `/`)
✅ Will be deployed to GitHub Pages as the root page
✅ GitHub Actions configured for auto-deployment
✅ Manual build option available via `make build-landing`

## Next: Deploy to GitHub Pages

Once you verify it works locally, deploy it:

```bash
# Option 1: Auto-deploy via GitHub Actions
git add .
git commit -m "Add landing page for GitHub Pages"
git push public main
# Then enable GitHub Actions in repo settings

# Option 2: Manual deploy
make build-landing
git add docs/
git commit -m "Add GitHub Pages site"
git push public main
# Then configure Pages to use /docs folder
```
