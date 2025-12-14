import { NextRequest, NextResponse } from 'next/server'
import { mergeTenantHeaders, resolveTenantIdFromRequest } from '@/lib/tenant'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'
    const tenantId = resolveTenantIdFromRequest(request)

    // Get authorization header from the incoming request
    const authHeader = request.headers.get('authorization')
    const baseHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    // Add authorization header if present
    if (authHeader) {
      baseHeaders['Authorization'] = authHeader
    }

    const headers = mergeTenantHeaders(tenantId, baseHeaders)

    const response = await fetch(`${apiUrl}/api/connection/switch`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error switching connection:', error)
    return NextResponse.json(
      {
        success: false,
        message: 'Failed to switch connection',
        details: null
      },
      { status: 500 }
    )
  }
}
