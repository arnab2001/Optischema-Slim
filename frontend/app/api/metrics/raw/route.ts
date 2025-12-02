import { NextRequest, NextResponse } from 'next/server'
import { mergeTenantHeaders, resolveTenantIdFromRequest } from '@/lib/tenant'

export async function GET(request: NextRequest) {
  try {
    // Pass through query parameters for pagination, filtering, etc.
    const { searchParams } = new URL(request.url)
    const queryString = searchParams.toString()
    const backendUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/metrics/raw${queryString ? `?${queryString}` : ''}`
    const tenantId = resolveTenantIdFromRequest(request)

    // Get authorization header from the incoming request
    const authHeader = request.headers.get('authorization')
    const baseHeaders: Record<string, string> = {}

    // Add authorization header if present
    if (authHeader) {
      baseHeaders['Authorization'] = authHeader
    }

    const headers = mergeTenantHeaders(tenantId, baseHeaders)

    const response = await fetch(backendUrl, {
      headers: headers,
    })
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Metrics fetch error:', error)
    return NextResponse.json({
      error: 'Failed to fetch metrics',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 })
  }
}
