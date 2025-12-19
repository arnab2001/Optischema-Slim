import { NextRequest, NextResponse } from 'next/server'
import { forwardToBackend } from '@/lib/apiMiddleware'

export async function GET(request: NextRequest) {
  try {
    const response = await forwardToBackend(
      request,
      '/api/health/latest',
      {
        method: 'GET',
      }
    )

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json(
          {
            error: 'No health scan results found',
            details: 'Run a health scan first'
          },
          { status: 404 }
        )
      }
      
      const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch scan results' }))
      return NextResponse.json(
        {
          error: errorData.detail || 'Failed to fetch scan results',
          details: errorData
        },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Health scan fetch error:', error)
    return NextResponse.json(
      {
        error: 'Failed to fetch health scan results',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
}





