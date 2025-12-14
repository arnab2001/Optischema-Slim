import { NextRequest, NextResponse } from 'next/server'
import { mergeTenantHeaders, resolveTenantIdFromRequest } from '@/lib/tenant'

export async function GET(request: NextRequest) {
  try {
    const backendUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/metrics/trends`
    const tenantId = resolveTenantIdFromRequest(request)

    const response = await fetch(backendUrl, {
      headers: mergeTenantHeaders(tenantId),
    })
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Trends fetch error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch trends data' },
      { status: 500 }
    )
  }
} 
