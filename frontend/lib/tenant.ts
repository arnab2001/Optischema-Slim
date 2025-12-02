export const DEFAULT_TENANT_ID = '00000000-0000-0000-0000-000000000001'

export function resolveTenantIdFromRequest(request: Request): string {
  const header = request.headers.get('x-tenant-id')
  if (header && header.trim().length > 0) {
    return header
  }
  return DEFAULT_TENANT_ID
}

export function mergeTenantHeaders(
  tenantId: string,
  baseHeaders?: HeadersInit
): HeadersInit {
  if (!baseHeaders) {
    return { 'X-Tenant-ID': tenantId }
  }

  if (baseHeaders instanceof Headers) {
    const headers = new Headers(baseHeaders)
    headers.set('X-Tenant-ID', tenantId)
    return headers
  }

  if (Array.isArray(baseHeaders)) {
    return [
      ...baseHeaders.filter(([key]) => key.toLowerCase() !== 'x-tenant-id'),
      ['X-Tenant-ID', tenantId],
    ]
  }

  return {
    ...baseHeaders,
    'X-Tenant-ID': tenantId,
  }
}
