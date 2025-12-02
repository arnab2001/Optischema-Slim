import { NextRequest, NextResponse } from 'next/server'
import { mergeTenantHeaders, resolveTenantIdFromRequest } from '@/lib/tenant'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const timeRange = searchParams.get('time_range') || '1h'
    const interval = searchParams.get('interval') || '5m'
    const backendUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/metrics/historical?time_range=${timeRange}&interval=${interval}`
    const tenantId = resolveTenantIdFromRequest(request)

    const response = await fetch(backendUrl, {
      headers: mergeTenantHeaders(tenantId),
    })
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Historical metrics fetch error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch historical metrics' },
      { status: 500 }
    )
  }
} 
