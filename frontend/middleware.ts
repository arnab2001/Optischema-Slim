// middleware.ts
import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  // For API routes, we need to ensure headers like Authorization are passed through
  // Next.js rewrites don't automatically pass dynamic headers from the client request
  if (request.nextUrl.pathname.startsWith('/api/')) {
    // Clone the headers to modify them
    const headers = new Headers(request.headers);

    // Set a default tenant ID if not present
    if (!headers.has('X-Tenant-ID')) {
      headers.set('X-Tenant-ID', '00000000-0000-0000-0000-000000000001');
    }

    // The request will go through Next.js rewrites, but this ensures headers are properly set
    // when the rewrites process the request

    // Create a new request with the updated headers
    const requestWithHeaders = new NextRequest(request, {
      headers,
    });

    return NextResponse.next({
      request: requestWithHeaders,
    });
  }

  return NextResponse.next();
}

// Configure which paths the middleware should run on
export const config = {
  matcher: '/api/:path*',
};