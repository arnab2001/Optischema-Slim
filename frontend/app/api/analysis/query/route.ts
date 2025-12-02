import { NextResponse } from 'next/server'
import { mergeTenantHeaders, resolveTenantIdFromRequest } from '@/lib/tenant'

export async function POST(request: Request) {
  try {
    const { query, explain = true, optimize = true } = await request.json()
    
    if (!query) {
      return NextResponse.json({ 
        error: 'Missing query parameter' 
      }, { status: 400 })
    }

    const tenantId = resolveTenantIdFromRequest(request)
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/analysis/query`, {
      method: 'POST',
      headers: mergeTenantHeaders(tenantId, {
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({ 
        query,
        explain,
        optimize
      })
    })
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Query analysis error:', error)
    return NextResponse.json({ 
      error: 'Failed to analyze query',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 })
  }
} 
