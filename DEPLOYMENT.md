# Deployment Guide

## GitHub Pages Landing Page

The landing page is available at `/landing` in development mode and deployed to GitHub Pages for public access.

### Local Development

1. **View the landing page locally:**
   ```bash
   make dev-frontend
   # Then visit: http://localhost:3000/landing
   ```

2. **Build the landing page for GitHub Pages:**
   ```bash
   make build-landing
   ```
   This will create a `docs/` directory with the static site.

### GitHub Pages Deployment

#### Option 1: Automatic Deployment (Recommended)

The repository is configured with GitHub Actions for automatic deployment:

1. **Push to main branch:**
   ```bash
   git add .
   git commit -m "Update landing page"
   git push public main
   ```

2. **Enable GitHub Pages (first time only):**
   - Go to: https://github.com/arnab2001/Optischema-Slim/settings/pages
   - Source: **GitHub Actions**
   - Save

3. **Access your landing page:**
   - URL: https://arnab2001.github.io/Optischema-Slim/

#### Option 2: Manual Deployment (from docs/ folder)

If you prefer to deploy from the `docs/` folder:

1. **Build the landing page:**
   ```bash
   make build-landing
   ```

2. **Commit and push:**
   ```bash
   git add docs/
   git commit -m "Update GitHub Pages site"
   git push public main
   ```

3. **Configure GitHub Pages:**
   - Go to: https://github.com/arnab2001/Optischema-Slim/settings/pages
   - Source: Deploy from a branch
   - Branch: **main**
   - Folder: **/docs**
   - Save

4. **Access your landing page:**
   - URL: https://arnab2001.github.io/Optischema-Slim/

### Landing Page vs Dashboard

- **Landing Page** (`/landing`): Public-facing marketing page, deployed to GitHub Pages
- **Dashboard** (`/dashboard`): Application interface, runs locally with Docker

The landing page is a static site that can be deployed anywhere, while the dashboard requires the backend API and database.

### Customizing the Landing Page

Edit the landing page:
```
frontend/app/landing/page.tsx
```

After making changes:
```bash
# Test locally
make dev-frontend
# Visit: http://localhost:3000/landing

# Build for GitHub Pages
make build-landing

# Deploy
git add docs/
git commit -m "Update landing page"
git push public main
```

### Troubleshooting

**Issue: Images not loading on GitHub Pages**
- Make sure `EXPORT_MODE=true` is set during build
- Images are automatically set to `unoptimized: true` for static export

**Issue: Links not working**
- GitHub Pages uses `/Optischema-Slim` as basePath
- All routes are automatically prefixed during export

**Issue: 404 errors**
- The build script creates a 404.html for SPA routing
- Make sure `.nojekyll` file exists in docs/

**Issue: Build fails**
- Check Node.js version (18+ required)
- Run `npm install` in frontend/ directory
- Check for TypeScript errors: `cd frontend && npm run lint`
