import { NextRequest, NextResponse } from 'next/server'
import { forwardToBackend } from '@/lib/apiMiddleware'

export async function POST(request: NextRequest) {
  try {
    const response = await forwardToBackend(
      request,
      '/api/health/scan',
      {
        method: 'POST',
      }
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Health scan failed' }))
      return NextResponse.json(
        {
          error: errorData.detail || 'Health scan failed',
          details: errorData
        },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Health scan error:', error)
    return NextResponse.json(
      {
        error: 'Failed to trigger health scan',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
}




