import { NextRequest, NextResponse } from 'next/server'
import { forwardToBackend } from '@/lib/apiMiddleware'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    const response = await forwardToBackend(
      request,
      '/api/connection/test',
      {
        method: 'POST',
        body: JSON.stringify(body),
        additionalHeaders: {
          'Content-Type': 'application/json',
        }
      }
    )

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error testing connection:', error)
    return NextResponse.json(
      {
        success: false,
        message: 'Failed to test connection',
        details: null
      },
      { status: 500 }
    )
  }
}
