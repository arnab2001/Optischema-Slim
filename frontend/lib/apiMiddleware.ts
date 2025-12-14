import { NextRequest } from 'next/server';
import { mergeTenantHeaders, resolveTenantIdFromRequest } from './tenant';

/**
 * Creates headers for forwarding requests to backend API
 * Includes tenant ID and authorization headers from the original request
 */
export function createBackendHeaders(request: NextRequest, additionalHeaders: Record<string, string> = {}) {
  const tenantId = resolveTenantIdFromRequest(request);

  // Get authorization header from the incoming request
  const authHeader = request.headers.get('authorization');

  const baseHeaders: Record<string, string> = { ...additionalHeaders };

  // Add authorization header if present
  if (authHeader) {
    baseHeaders['Authorization'] = authHeader;
  }

  // Merge with tenant headers
  return mergeTenantHeaders(tenantId, baseHeaders);
}

/**
 * Forward a request to the backend API with proper headers
 */
export async function forwardToBackend(
  request: NextRequest,
  backendEndpoint: string,
  options: {
    method?: string;
    body?: string | Buffer;
    additionalHeaders?: Record<string, string>;
  } = {}
) {
  const { method = 'GET', body, additionalHeaders = {} } = options;

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
  const headers = createBackendHeaders(request, additionalHeaders);

  const response = await fetch(`${apiUrl}${backendEndpoint}`, {
    method,
    headers,
    body,
  });

  return response;
}