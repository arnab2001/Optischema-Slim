import { NextResponse } from 'next/server'
import { mergeTenantHeaders, resolveTenantIdFromRequest } from '@/lib/tenant'

export async function POST(request: Request) {
  try {
    const { recommendation_id, action } = await request.json()
    
    if (!recommendation_id) {
      return NextResponse.json({ 
        error: 'Missing recommendation_id' 
      }, { status: 400 })
    }

    // Determine the endpoint based on action
    const endpoint = action === 'rollback' 
      ? `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/suggestions/apply`
      : `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/suggestions/apply`;

    const tenantId = resolveTenantIdFromRequest(request)
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: mergeTenantHeaders(tenantId, {
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({ recommendation_id, action })
    })
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Suggestion application error:', error)
    return NextResponse.json({ 
      error: 'Failed to apply suggestion',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 })
  }
} 
