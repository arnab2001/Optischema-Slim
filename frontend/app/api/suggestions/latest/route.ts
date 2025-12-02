import { NextResponse } from 'next/server'
import { forwardToBackend } from '@/lib/apiMiddleware'

export async function GET(request: Request) {
  try {
    const nextRequest = request as import('next/server').NextRequest;

    const response = await forwardToBackend(
      nextRequest,
      '/suggestions/latest'
    )

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Suggestions fetch error:', error)
    return NextResponse.json({
      error: 'Failed to fetch suggestions',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 })
  }
}
