/**
 * Waitlist API client for Supabase Edge Function
 */

const WAITLIST_ENDPOINT = 'https://lnvkeysarmzdprtmufwt.supabase.co/functions/v1/waitlist'

export interface WaitlistResponse {
  status: 'ok'
  email: string
  confirmed: boolean
  token?: string
  emailSent: boolean
}

export interface WaitlistError {
  error: string
}

export async function joinWaitlist(email: string): Promise<WaitlistResponse> {
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
  
  const response = await fetch(WAITLIST_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${anonKey}`,
      'apikey': anonKey,
    },
    body: JSON.stringify({ email: email.trim() }),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error((data as WaitlistError).error || 'Failed to join waitlist')
  }

  return data as WaitlistResponse
}

/**
 * Validate email format
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email.trim())
}
