import { NextRequest, NextResponse } from 'next/server'
import { mergeTenantHeaders, resolveTenantIdFromRequest } from '@/lib/tenant'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const tenantId = resolveTenantIdFromRequest(request)
    const response = await fetch(`${BACKEND_URL}/api/connection/pg-stat-info`, {
      method: 'GET',
      headers: mergeTenantHeaders(tenantId, {
        'Content-Type': 'application/json',
      }),
    })

    const data = await response.json()
    
    return NextResponse.json(data, {
      status: response.status,
    })
  } catch (error) {
    console.error('Failed to get pg_stat_statements info:', error)
    return NextResponse.json(
      { error: 'Failed to get pg_stat_statements info' },
      { status: 500 }
    )
  }
} 
