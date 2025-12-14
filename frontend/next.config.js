/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Use Docker service name for containerized environment
    const backendUrl = 'http://optischema-api:8080';

    return [
      {
        source: '/api/metrics/:path*',
        destination: `${backendUrl}/api/metrics/:path*`,
      },
      {
        source: '/api/suggestions/latest',
        destination: `${backendUrl}/suggestions/latest`,
      },
      {
        source: '/api/suggestions/generate',
        destination: `${backendUrl}/suggestions/generate`,
      },
      {
        source: '/api/suggestions/apply',
        destination: `${backendUrl}/suggestions/apply`,
      },
      {
        source: '/api/suggestions/benchmark',
        destination: `${backendUrl}/suggestions/benchmark`,
      },
      {
        source: '/api/suggestions/rollback',
        destination: `${backendUrl}/suggestions/rollback`,
      },
      {
        source: '/api/health/:path*',
        destination: `${backendUrl}/api/health/:path*`,
      },
      {
        source: '/api/connection/:path*',
        destination: `${backendUrl}/api/connection/:path*`,
      },
      {
        source: '/api/analysis/:path*',
        destination: `${backendUrl}/analysis/:path*`,
      },
      // P0 Features - Audit Logging
      {
        source: '/api/audit/:path*',
        destination: `${backendUrl}/api/audit/:path*`,
      },
      // P0 Features - Connection Baselines
      {
        source: '/api/connection-baseline/:path*',
        destination: `${backendUrl}/api/connection-baseline/:path*`,
      },
      // P0 Features - Index Advisor
      {
        source: '/api/index-advisor/:path*',
        destination: `${backendUrl}/api/index-advisor/:path*`,
      },
      // Apply Manager - Apply/Rollback operations
      {
        source: '/api/apply/:path*',
        destination: `${backendUrl}/api/apply/:path*`,
      },
    ]
  },
}

module.exports = nextConfig 