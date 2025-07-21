import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    console.log('Apply-and-test request:', body);
    
    // Forward the request to the backend - use Docker service name
    const backendResponse = await fetch('http://optischema-api:8000/suggestions/apply-and-test', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await backendResponse.json();
    console.log('Backend response status:', backendResponse.status);
    console.log('Backend response data:', data);

    if (!backendResponse.ok) {
      const errorMessage = data.message || data.detail || 'Apply and test failed';
      console.error('Backend error:', errorMessage);
      return NextResponse.json(
        { 
          error: errorMessage,
          success: false,
          message: errorMessage,
          details: data 
        },
        { status: backendResponse.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Apply and test API error:', error);
    return NextResponse.json(
      { 
        error: `Internal server error: ${error}`,
        success: false,
        message: `Frontend API error: ${error}` 
      },
      { status: 500 }
    );
  }
} 