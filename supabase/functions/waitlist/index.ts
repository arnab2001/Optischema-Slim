import { createClient } from "npm:@supabase/supabase-js@2.34.0";

// CORS headers for all responses
const corsHeaders = {
  'Access-Control-Allow-Origin': '*', // For development - in production, set to your specific domain
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, apikey, x-client-info',
  'Access-Control-Allow-Credentials': 'true',
};

Deno.serve(async (req: Request) => {
  // Handle CORS preflight OPTIONS request
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: corsHeaders,
    });
  }

  try {
    // Only allow POST for actual requests
    if (req.method !== 'POST') {
      return new Response(
        JSON.stringify({ error: 'Method not allowed' }), 
        { 
          status: 405, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      );
    }

    const body = await req.json().catch(() => null);
    const email = body?.email?.toString().trim();
    
    if (!email) {
      return new Response(
        JSON.stringify({ error: 'Email is required' }), 
        { 
          status: 400, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      );
    }

    const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!;
    const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    
    if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
      return new Response(
        JSON.stringify({ error: 'Missing Supabase environment variables' }), 
        { 
          status: 500, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      );
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, { 
      auth: { persistSession: false } 
    });

    // Generate confirmation token
    const token = crypto.randomUUID();

    // Upsert the email, only set token if new or not confirmed
    const { data, error } = await supabase
      .from('waitlist')
      .upsert(
        { email, confirm_token: token },
        { onConflict: 'email', ignoreDuplicates: false }
      )
      .select()
      .limit(1);

    if (error) {
      console.error('DB error', error);
      return new Response(
        JSON.stringify({ error: 'Database error' }), 
        { 
          status: 500, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      );
    }

    // Get the inserted or updated row
    const row = Array.isArray(data) ? data[0] : data;

    // Check if email provider is configured
    const EMAIL_PROVIDER = Deno.env.get('MAIL_PROVIDER') || '';
    let emailSent = false;
    
    if (EMAIL_PROVIDER) {
      // Placeholder for sending email - implement your email provider here
      // For example: SendGrid, Resend, AWS SES, etc.
    }

    const resp = { 
      status: 'ok', 
      email: row.email, 
      confirmed: row.confirmed, 
      token: EMAIL_PROVIDER ? undefined : token, 
      emailSent 
    };
    
    return new Response(
      JSON.stringify(resp), 
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    );
  } catch (e) {
    console.error(e);
    return new Response(
      JSON.stringify({ error: 'Internal server error' }), 
      { 
        status: 500, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    );
  }
});
