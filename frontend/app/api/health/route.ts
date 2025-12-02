import { NextResponse } from 'next/server'
import { createBackendHeaders, forwardToBackend } from '@/lib/apiMiddleware'

export async function GET(request: Request) {
  try {
    const nextRequest = request as import('next/server').NextRequest;

    const response = await forwardToBackend(
      nextRequest,
      '/health'
    );

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Health check error:', error)
    return NextResponse.json({
      status: 'unhealthy',
      error: 'Failed to check backend health',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 })
  }
}
