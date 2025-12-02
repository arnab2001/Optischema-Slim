import { NextRequest, NextResponse } from 'next/server'
import { mergeTenantHeaders, resolveTenantIdFromRequest } from '@/lib/tenant'

export async function POST(request: NextRequest) {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const tenantId = resolveTenantIdFromRequest(request)

    // Get authorization header from the incoming request
    const authHeader = request.headers.get('authorization')
    const baseHeaders: Record<string, string> = {}

    // Add authorization header if present
    if (authHeader) {
      baseHeaders['Authorization'] = authHeader
    }

    const headers = mergeTenantHeaders(tenantId, baseHeaders)

    const response = await fetch(`${apiUrl}/api/connection/disconnect`, {
      method: 'POST',
      headers: headers,
    })

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error disconnecting:', error)
    return NextResponse.json(
      {
        success: false,
        message: 'Failed to disconnect'
      },
      { status: 500 }
    )
  }
}
