'use client'

import Link from 'next/link'
import Image from 'next/image'
import { Database, Zap, Shield, TrendingUp, Github, ArrowRight, Mail, CheckCircle2, AlertCircle } from 'lucide-react'
import { useState } from 'react'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Navigation */}
      <nav className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <Database className="w-8 h-8 text-blue-600" />
              <span className="text-xl font-bold">OptiSchema Slim</span>
            </div>
            <div className="flex items-center gap-4">
              <a 
                href="https://github.com/arnab2001/Optischema-Slim" 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2 text-sm hover:text-blue-600 transition-colors"
              >
                <Github className="w-4 h-4" />
                GitHub
              </a>
              <Link 
                href="/dashboard" 
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-bold text-slate-900 mb-6">
            PostgreSQL Performance,{' '}
            <span className="text-blue-600">Simplified</span>
          </h1>
          <p className="text-xl text-slate-600 mb-8">
            Local-first PostgreSQL optimization tool. Analyze queries, get AI-powered recommendations, 
            and improve your database performance—all without sharing your data.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link 
              href="/dashboard"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-lg font-medium"
            >
              Try It Now
              <ArrowRight className="w-5 h-5" />
            </Link>
            <a 
              href="https://github.com/arnab2001/Optischema-Slim"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 border-2 border-slate-300 text-slate-700 rounded-lg hover:border-slate-400 transition-colors text-lg font-medium"
            >
              <Github className="w-5 h-5" />
              View on GitHub
            </a>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          <FeatureCard
            icon={<Shield className="w-8 h-8 text-blue-600" />}
            title="Privacy First"
            description="Run locally on your machine. Your data never leaves your infrastructure."
          />
          <FeatureCard
            icon={<Zap className="w-8 h-8 text-blue-600" />}
            title="AI-Powered"
            description="Get intelligent recommendations using Ollama, OpenAI, or Gemini."
          />
          <FeatureCard
            icon={<TrendingUp className="w-8 h-8 text-blue-600" />}
            title="Real-time Analysis"
            description="Monitor query performance and identify bottlenecks instantly."
          />
          <FeatureCard
            icon={<Database className="w-8 h-8 text-blue-600" />}
            title="Zero Dependencies"
            description="Just Docker. No complex setup or external services required."
          />
        </div>
      </section>

      {/* How It Works */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
        <div className="grid md:grid-cols-3 gap-8">
          <StepCard
            number="1"
            title="Connect Your Database"
            description="Point OptiSchema to your PostgreSQL database with a simple connection string."
          />
          <StepCard
            number="2"
            title="Analyze Queries"
            description="Automatically detect slow queries and performance bottlenecks in real-time."
          />
          <StepCard
            number="3"
            title="Get Recommendations"
            description="Receive AI-powered optimization suggestions and apply them with confidence."
          />
        </div>
      </section>

      {/* Quick Start */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="bg-slate-900 rounded-2xl p-8 md:p-12 text-white">
          <h2 className="text-3xl font-bold mb-4">Quick Start</h2>
          <p className="text-slate-300 mb-6">Get up and running in under 2 minutes:</p>
          <div className="bg-slate-800 rounded-lg p-6 font-mono text-sm mb-6 overflow-x-auto">
            <div className="text-green-400"># Clone the repository</div>
            <div className="text-slate-300">git clone https://github.com/arnab2001/Optischema-Slim.git</div>
            <div className="text-slate-300 mt-2">cd Optischema-Slim</div>
            <div className="text-green-400 mt-4"># Start with Docker</div>
            <div className="text-slate-300">docker compose up --build</div>
            <div className="text-green-400 mt-4"># Open your browser</div>
            <div className="text-slate-300">http://localhost:3000</div>
          </div>
          <a 
            href="https://github.com/arnab2001/Optischema-Slim#readme"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
          >
            View full documentation
            <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </section>

      {/* Waitlist Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="max-w-3xl mx-auto">
          <WaitlistSection />
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
        <h2 className="text-4xl font-bold mb-4">Ready to optimize your PostgreSQL?</h2>
        <p className="text-xl text-slate-600 mb-8">Start analyzing your queries in minutes.</p>
        <Link 
          href="/dashboard"
          className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-lg font-medium"
        >
          Get Started Now
          <ArrowRight className="w-5 h-5" />
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t mt-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-3">
              <Database className="w-6 h-6 text-blue-600" />
              <span className="font-semibold">OptiSchema Slim</span>
            </div>
            <div className="flex gap-6 text-sm text-slate-600">
              <a 
                href="https://github.com/arnab2001/Optischema-Slim"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-blue-600 transition-colors"
              >
                GitHub
              </a>
              <a 
                href="https://github.com/arnab2001/Optischema-Slim/issues"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-blue-600 transition-colors"
              >
                Issues
              </a>
              <Link href="/dashboard" className="hover:text-blue-600 transition-colors">
                Dashboard
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="p-6 bg-white rounded-xl border border-slate-200 hover:border-blue-300 transition-colors">
      <div className="mb-4">{icon}</div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-slate-600 text-sm">{description}</p>
    </div>
  )
}

function StepCard({ number, title, description }: { number: string; title: string; description: string }) {
  return (
    <div className="relative">
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center text-xl font-bold">
          {number}
        </div>
        <div>
          <h3 className="text-xl font-semibold mb-2">{title}</h3>
          <p className="text-slate-600">{description}</p>
        </div>
      </div>
    </div>
  )
}

function WaitlistSection() {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!email.trim()) {
      setStatus('error')
      setMessage('Please enter your email')
      return
    }

    setStatus('loading')
    setMessage('')

    try {
      console.log('Submitting email to waitlist:', email.trim())
      
      // Get anon key from environment or use hardcoded fallback
      const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_WrIS4GLRZwLP8LJZi8TjfQ_cCPvoYZQ'
      
      console.log('Anon key loaded:', anonKey ? '✅ Yes' : '❌ No')
      console.log('Key preview:', anonKey.substring(0, 20) + '...')
      
      if (!anonKey) {
        throw new Error('Supabase key not configured. Please check environment variables.')
      }
      
      const response = await fetch('https://lnvkeysarmzdprtmufwt.supabase.co/functions/v1/waitlist', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${anonKey}`,
          'apikey': anonKey,
        },
        body: JSON.stringify({ email: email.trim() }),
      })

      console.log('Response status:', response.status)
      
      // Try to parse JSON, but handle cases where it might not be JSON
      let data
      try {
        data = await response.json()
        console.log('Response data:', data)
      } catch (parseError) {
        console.error('Failed to parse response as JSON:', parseError)
        throw new Error('Invalid response from server. Please try again.')
      }

      if (!response.ok) {
        console.error('Request failed:', data)
        throw new Error(data.error || 'Failed to join waitlist')
      }

      setStatus('success')
      setMessage(data.confirmed 
        ? 'You\'re already on the list! We\'ll keep you updated.' 
        : 'Awesome! You\'re on the waitlist. We\'ll notify you when OptiSchema Slim is ready!')
      setEmail('')
    } catch (error) {
      console.error('Waitlist submission error:', error)
      setStatus('error')
      
      // Check if it's a network error (CORS)
      if (error instanceof TypeError && error.message.includes('fetch')) {
        setMessage('Network error. Please check your internet connection or try again later.')
      } else {
        setMessage(error instanceof Error ? error.message : 'Something went wrong. Please try again.')
      }
    }
  }

  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl p-8 md:p-12 text-center border border-blue-100">
      <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 text-white rounded-full mb-6">
        <Mail className="w-8 h-8" />
      </div>
      
      <h2 className="text-3xl font-bold mb-4 text-slate-900">
        Join the Waitlist
      </h2>
      <p className="text-lg text-slate-600 mb-8 max-w-2xl mx-auto">
        Be the first to know about new features, updates, and exclusive early access opportunities.
      </p>

      <form onSubmit={handleSubmit} className="max-w-md mx-auto">
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email"
            disabled={status === 'loading' || status === 'success'}
            className="flex-1 px-4 py-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed"
            required
          />
          <button
            type="submit"
            disabled={status === 'loading' || status === 'success'}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:bg-slate-400 disabled:cursor-not-allowed flex items-center justify-center gap-2 whitespace-nowrap"
          >
            {status === 'loading' ? (
              <>
                <span className="animate-spin">⏳</span>
                Joining...
              </>
            ) : status === 'success' ? (
              <>
                <CheckCircle2 className="w-5 h-5" />
                Joined!
              </>
            ) : (
              'Join Waitlist'
            )}
          </button>
        </div>

        {/* Status Messages */}
        {message && (
          <div className={`mt-4 p-3 rounded-lg flex items-center gap-2 ${
            status === 'success' 
              ? 'bg-green-50 text-green-800 border border-green-200' 
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
            {status === 'success' ? (
              <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
            )}
            <span className="text-sm">{message}</span>
          </div>
        )}
      </form>

      <p className="text-xs text-slate-500 mt-6">
        We respect your privacy. Unsubscribe at any time.
      </p>
    </div>
  )
}
