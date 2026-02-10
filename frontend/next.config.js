const nextConfig = {
  // Always use static export for the All-In-One build
  output: 'export',
  trailingSlash: true,

  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },

  // Skip linting and type checking during builds
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },

  // Static export doesn't support redirects, rewrites, or headers
  // we will handle routing in the FastAPI backend
}

module.exports = nextConfig 