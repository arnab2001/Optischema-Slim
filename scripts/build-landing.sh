#!/bin/bash
# Build script for GitHub Pages landing page

set -e

echo "🚀 Building landing page for GitHub Pages..."

# Navigate to frontend directory
cd "$(dirname "$0")/../frontend"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build and export with GitHub Pages configuration
echo "📦 Building Next.js app for static export..."
EXPORT_MODE=true npm run build

# Create docs directory for GitHub Pages
echo "📁 Creating docs directory..."
rm -rf ../docs
mkdir -p ../docs

# Copy the exported site
if [ -d "out" ]; then
    echo "✅ Copying exported site..."
    cp -r out/* ../docs/
else
    echo "❌ Export failed - out/ directory not found"
    echo "Make sure 'output: export' is configured in next.config.js"
    exit 1
fi

# Create a .nojekyll file to disable Jekyll processing
touch ../docs/.nojekyll

# Create a custom 404 page for SPA routing
if [ -f "../docs/404.html" ]; then
    echo "✅ 404 page already exists"
else
    cp ../docs/index.html ../docs/404.html 2>/dev/null || true
fi

echo ""
echo "✨ Landing page built successfully!"
echo "📍 Output location: docs/"
echo ""
echo "Next steps:"
echo "1. Commit the docs/ directory:"
echo "   git add docs/"
echo "   git commit -m 'Add GitHub Pages landing page'"
echo "   git push public main"
echo ""
echo "2. Enable GitHub Pages:"
echo "   - Go to: https://github.com/arnab2001/Optischema-Slim/settings/pages"
echo "   - Source: Deploy from a branch"
echo "   - Branch: main"
echo "   - Folder: /docs"
echo "   - Click Save"
echo ""
echo "3. Your landing page will be available at:"
echo "   https://arnab2001.github.io/Optischema-Slim/"
echo ""
