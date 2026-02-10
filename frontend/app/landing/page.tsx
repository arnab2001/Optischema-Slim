import type * as React from "react";

'use client'

import { ArrowRight, CheckCircle2, ChevronRight, Terminal, Zap, Shield, Activity, Cpu, Mail, Star, Github, ArrowUpRight, Check, X, AlertCircle, Database } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'

export default function LandingPage() {
  const scrollToWaitlist = (e: React.MouseEvent) => {
    e.preventDefault()
    const element = document.getElementById('waitlist')
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' })
    }
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA] text-slate-900 selection:bg-indigo-500/20 selection:text-indigo-900 font-sans overflow-x-hidden">
      {/* Noise Overlay */}
      <div className="fixed inset-0 z-[9999] pointer-events-none opacity-[0.03] mix-blend-multiply"
        style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }}
      />

      {/* 1. Dynamic Background Grid with Beams */}
      <div className="fixed inset-0 z-0 pointer-events-none bg-slate-50">

        {/* Base Grid - Increased Opacity */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]" />

        {/* Radial Spotlight */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_800px_at_50%_200px,#C9EBFF,transparent)] opacity-20" />

        {/* Accent Patches (Restored) */}
        <div className="absolute left-0 right-0 top-0 -z-10 m-auto h-[310px] w-[310px] rounded-full bg-blue-400 opacity-20 blur-[100px]"></div>
        <div className="absolute right-0 bottom-0 -z-10 h-[310px] w-[310px] rounded-full bg-indigo-400 opacity-20 blur-[100px]"></div>

        {/* THE NEW BEAMS: Animated flowing lines */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-[20%] left-0 h-[1px] w-full animate-beam-horizontal bg-gradient-to-r from-transparent via-blue-400/50 to-transparent" />
          <div className="absolute top-[40%] left-0 h-[1px] w-full animate-beam-horizontal delay-1000 bg-gradient-to-r from-transparent via-indigo-400/50 to-transparent" />
          <div className="absolute top-0 left-[20%] w-[1px] h-full animate-beam-vertical delay-500 bg-gradient-to-b from-transparent via-blue-400/50 to-transparent" />
          <div className="absolute top-0 left-[80%] w-[1px] h-full animate-beam-vertical delay-2000 bg-gradient-to-b from-transparent via-indigo-400/50 to-transparent" />
        </div>

        {/* Vignette */}
        <div className="absolute inset-0 bg-gradient-to-t from-white via-transparent to-transparent" />
      </div>

      {/* Navigation */}
      <nav className="fixed w-full top-0 z-50 transition-all duration-300 border-b border-white/10 bg-white/50 backdrop-blur-md supports-[backdrop-filter]:bg-white/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="cursor-default">
              <OptiSchemaLogo />
            </div>
            <div className="flex items-center gap-4">
              <a
                href="https://github.com/arnab2001/Optischema-Slim"
                target="_blank"
                className="hidden sm:flex items-center group border border-slate-200 rounded-md overflow-hidden h-8"
              >
                <div className="px-3 py-2 bg-slate-50 text-xs font-medium text-slate-600 group-hover:bg-slate-100 border-r border-slate-200 transition-colors flex items-center gap-2">
                  <Github className="w-3.5 h-3.5" />
                  Star
                </div>
                <div className="px-2 py-2 bg-white text-xs font-mono text-slate-500">
                  :) {/* Static for now, or fetch dynamically */}
                </div>
              </a>
              <button
                onClick={scrollToWaitlist}
                className="group relative px-5 py-2 bg-slate-900 text-white rounded-lg overflow-hidden transition-all hover:shadow-[0_0_20px_-5px_rgba(0,0,0,0.3)]"
              >
                <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-shimmer" />
                <span className="relative text-sm font-medium flex items-center gap-2">
                  Request Early Access <ArrowUpRight className="w-3 h-3 opacity-50" />
                </span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16 md:pt-32 md:pb-24 text-center">

        {/* Animated Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-slate-200 shadow-sm text-slate-600 text-xs font-medium mb-8 animate-fade-in-up hover:border-blue-300 transition-colors cursor-default">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
          </span>
          Private Developer Preview
        </div>

        <h1 className="max-w-5xl mx-auto text-5xl md:text-7xl font-bold text-slate-900 mb-8 tracking-tight leading-[1.1]">
          The <ShimmerText text="Local-First" /> Doctor<br /> for your PostgreSQL.
        </h1>

        <p className="max-w-3xl mx-auto text-lg md:text-xl font-medium text-slate-600 mb-4 leading-relaxed">
          For Backend Engineers and DBAs who want faster Postgres without the cloud security risk.
        </p>

        <p className="max-w-2xl mx-auto text-xl text-slate-500 mb-10 leading-relaxed">
          Debug queries, verify indexes with HypoPG, and optimize performance using local LLMs.
          <span className="text-slate-900 font-medium"> Zero data egress.</span>
        </p>

        {/* Symmetrical Social Proof / Result Badge */}
        <div className="flex justify-center my-8 animate-fade-in-up delay-200">
          <LiveBenchmarkPill />
        </div>

        <div className="flex flex-col items-center gap-8">
          <div className="flex flex-col sm:flex-row gap-5 justify-center items-center mt-2 mb-8 animate-fade-in-up delay-100">

            {/* 1. Primary: The "Liquid Shimmer" Button */}
            <button
              onClick={scrollToWaitlist}
              className="group relative inline-flex h-12 items-center justify-center overflow-hidden rounded-xl bg-blue-600 px-8 font-medium text-white shadow-[0_4px_14px_0_rgba(37,99,235,0.39)] transition-all duration-300 hover:bg-blue-700 hover:scale-[1.02] hover:shadow-[0_6px_20px_rgba(37,99,235,0.23)] focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2"
            >
              {/* The Shimmer Effect */}
              <span className="absolute inset-0 flex h-full w-full -translate-x-full animate-[shimmer_2.5s_infinite] bg-gradient-to-r from-transparent via-white/25 to-transparent group-hover:animate-none" />

              <span className="relative flex items-center gap-2">
                <Mail className="w-4 h-4" />
                <span>Request Early Access</span>
                <ArrowRight className="w-3 h-3 opacity-70 group-hover:translate-x-0.5 transition-transform" />
              </span>
            </button>

            {/* 2. Secondary: The "Terminal Source" Button */}
            {/* 2. Secondary: The "Terminal Source" Button */}
            <a
              href="https://github.com/arnab2001/Optischema-Slim"
              target="_blank"
              rel="noopener noreferrer"
              className="group relative inline-flex h-12 items-center justify-center gap-3 overflow-hidden rounded-xl border border-slate-200 bg-white px-6 text-slate-600 shadow-sm transition-all duration-300 hover:border-slate-300 hover:text-slate-900 hover:shadow-md"
            >
              <div className="absolute inset-0 bg-slate-50 opacity-0 transition-opacity group-hover:opacity-100" />

              <div className="relative flex items-center gap-3">
                <Github className="w-4 h-4" />
                <div className="flex flex-col items-start leading-none gap-0.5">
                  <span className="font-semibold text-sm">Build from Source</span>
                  <span className="font-mono text-[10px] text-slate-400 group-hover:text-blue-600 transition-colors">
                    git clone optischema...
                  </span>
                </div>
              </div>
            </a>
          </div>

          {/* Ecosystem Strip */}
          <div className="mt-2 mb-6 flex flex-col items-center gap-4 animate-fade-in-up delay-200">
            <p className="text-xs font-semibold tracking-widest text-slate-400 uppercase">
              Works seamlessly with
            </p>
            <div className="flex items-center gap-8 opacity-50 grayscale hover:grayscale-0 transition-all duration-500">
              {/* Simple Text Logos (Or use SVGs if you have them) */}
              <span className="text-lg font-bold text-slate-600 flex items-center gap-2">
                PostgreSQL
              </span>
              <span className="text-lg font-bold text-slate-600 flex items-center gap-2">
                Docker
              </span>
              <span className="text-lg font-bold text-slate-600 flex items-center gap-2">
                Supabase
              </span>
              <span className="text-lg font-bold text-slate-600 flex items-center gap-2">
                Neon
              </span>
            </div>
          </div>

          {/* Safety Strip */}
          <div className="flex items-center gap-4 text-xs font-medium text-slate-500 animate-fade-in-up delay-100">
            <span className="flex items-center gap-1"><Shield className="w-3 h-3" /> Read-only default</span>
            <span className="text-slate-300">•</span>
            <span className="flex items-center gap-1"><Shield className="w-3 h-3" /> No data egress</span>
            <span className="text-slate-300">•</span>
            <span className="flex items-center gap-1"><Zap className="w-3 h-3" /> Works with pg_stat_statements</span>
          </div>


        </div>
      </section>

      {/* Bento Grid Features */}
      <section className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          <SpotlightCard className="md:col-span-2">
            <div className="relative z-10 h-full flex flex-col justify-between">
              <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center mb-6 text-blue-600 border border-blue-100">
                <Activity className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-2xl font-bold mb-3 text-slate-900">Simulation-First Architecture</h3>
                <p className="text-slate-500 text-lg leading-relaxed max-w-md">
                  Don't guess. We use <code className="bg-slate-100 px-1.5 py-0.5 rounded text-slate-700 font-mono text-sm">hypopg</code> to create virtual indexes and verify cost reductions before you ever touch production.
                </p>
              </div>
              {/* Decorative Abstract Graph */}
              <div className="absolute right-0 bottom-0 w-1/3 h-24 opacity-90">
                <div className="flex items-end justify-end gap-1 h-full pr-6 pb-6">
                  {/* High Cost / Before */}
                  <div className="w-4 bg-red-400/80 rounded-t-sm" style={{ height: '85%' }}></div>
                  <div className="w-4 bg-red-300/80 rounded-t-sm" style={{ height: '65%' }}></div>
                  <div className="w-4 bg-slate-300/80 rounded-t-sm" style={{ height: '45%' }}></div>
                  {/* Low Cost / After */}
                  <div className="w-4 bg-green-500 rounded-t-sm" style={{ height: '20%' }}></div>
                  <div className="w-4 bg-blue-600 rounded-t-sm" style={{ height: '15%' }}></div>
                </div>
              </div>
            </div>
          </SpotlightCard>

          <SpotlightCard className="bg-[#0F172A] border-slate-800 group">
            <div className="relative z-10">
              <Shield className="w-10 h-10 text-emerald-400 mb-6" />
              <h3 className="text-xl font-bold mb-2 text-slate-900">Offline Capable</h3>
              <p className="text-slate-500 mb-6">
                Your schema and queries never leave your machine. Perfect for strict NDAs.
              </p>
              <div className="flex items-center gap-2 text-xs font-mono text-emerald-400/80 bg-emerald-400/10 w-fit px-2 py-1 rounded border border-emerald-400/20">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></div>
                localhost:5432
              </div>
            </div>
          </SpotlightCard>

          <SpotlightCard>
            <Cpu className="w-10 h-10 text-indigo-600 mb-6" />
            <h3 className="text-xl font-bold mb-2 text-slate-900">Model Agnostic</h3>
            <p className="text-slate-500 mb-4">
              Default to <strong>SQLCoder-7B</strong> via Ollama, or bring your own keys:
            </p>
            <div className="flex flex-wrap gap-2">
              <span className="px-2.5 py-1.5 bg-slate-100 text-slate-600 text-xs font-medium rounded-md flex items-center gap-1.5 cursor-default group-hover:bg-slate-200 transition-colors">
                <Zap className="w-3 h-3 text-slate-500" /> OpenAI
              </span>
              <span className="px-2.5 py-1.5 bg-slate-100 text-slate-600 text-xs font-medium rounded-md flex items-center gap-1.5 cursor-default group-hover:bg-slate-200 transition-colors">
                <Activity className="w-3 h-3 text-slate-500" /> DeepSeek
              </span>
              <span className="px-2.5 py-1.5 bg-slate-100 text-slate-600 text-xs font-medium rounded-md flex items-center gap-1.5 cursor-default group-hover:bg-slate-200 transition-colors">
                <Cpu className="w-3 h-3 text-slate-500" /> Gemini
              </span>
            </div>
          </SpotlightCard>

          {/* Zero Config Card-Fixed Whitespace */}
          <SpotlightCard className="md:col-span-2 bg-gradient-to-br from-indigo-50/50 to-blue-50/50 flex flex-col justify-center">
            <div className="flex flex-col md:flex-row items-center gap-8 h-full">
              <div className="flex-1">
                <h3 className="text-2xl font-bold mb-3 text-slate-900">Zero-Config Connection</h3>
                <p className="text-slate-600 text-lg">
                  Paste your connection string. We auto-detect stats extensions and configure the pipeline instantly.
                </p>
              </div>

              {/* Visual Filler for Whitespace */}
              <div className="w-full md:w-auto bg-white p-4 rounded-xl shadow-sm border border-slate-200/60 flex flex-col gap-3 min-w-[300px] transform md:-rotate-1 hover:rotate-0 transition-transform duration-300">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-2 h-2 rounded-full bg-slate-300"></div>
                  <span className="text-[10px] uppercase font-bold text-slate-500">Connection String</span>
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded p-2 flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <code className="text-xs font-mono text-slate-500 truncate">postgres://user:***@localhost:5432/db</code>
                </div>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-[10px] text-slate-500">Auto-detecting...</span>
                  <span className="text-[10px] font-bold text-green-600 bg-green-50 px-2 py-0.5 rounded-full flex items-center gap-1">
                    <Check className="w-3 h-3" /> Ready
                  </span>
                </div>
              </div>
            </div>
          </SpotlightCard>

        </div>
      </section>

      {/* Terminal Section */}
      <section className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-slate-900 mb-4">The Future Workflow</h2>
          <p className="text-slate-500">How you will deploy OptiSchema when the alpha drops.</p>
        </div>

        <div className="rounded-xl overflow-hidden shadow-2xl bg-[#1e1e1e] font-mono text-sm relative border border-slate-800 ring-1 ring-white/10">
          <div className="bg-[#252525] px-4 py-4 flex items-center gap-2 border-b border-[#333]">
            <div className="flex gap-2">
              <div className="w-3 h-3 rounded-full bg-[#FF5F56]"></div>
              <div className="w-3 h-3 rounded-full bg-[#FFBD2E]"></div>
              <div className="w-3 h-3 rounded-full bg-[#27C93F]"></div>
            </div>
            <div className="ml-4 text-gray-500 text-xs">sh — 80x24</div>
          </div>

          <div className="p-6 text-gray-300 min-h-[220px]">
            <TypewriterTerminal />
          </div>
        </div>
      </section>

      {/* Waitlist Section */}
      <section id="waitlist" className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 pb-32 scroll-mt-32">
        <WaitlistSection />
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto px-1 sm:px-2 lg:px-4 py-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">

            <OptiSchemaLogo />

            {/* <span className="font-semibold text-slate-700 text-sm">OptiSchema Slim © 2024</span> */}
          </div>
          <div className="flex gap-6 text-sm font-medium text-slate-500">
            <a href="https://github.com/arnab2001/Optischema-Slim" target="_blank" className="hover:text-blue-600 transition-colors">GitHub</a>
            <span className="text-slate-300">|</span>
            <span className="text-slate-500">Built for developers</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

// --- Components ---

function ShimmerText({ text }: { text: string }) {
  return (
    <span className="relative inline-block text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-indigo-500 to-blue-600 bg-[length:200%_auto] animate-text-shimmer">
      {text}
    </span>
  )
}

function SpotlightCard({ children, className = "" }: { children: React.ReactNode, className?: string }) {
  const divRef = useRef<HTMLDivElement>(null)
  const [isFocused, setIsFocused] = useState(false)
  const [position, setPosition] = useState({ x: 0, y: 0 })

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!divRef.current) return
    const rect = divRef.current.getBoundingClientRect()
    setPosition({ x: e.clientX - rect.left, y: e.clientY - rect.top })
  }

  return (
    <div
      ref={divRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsFocused(true)}
      onMouseLeave={() => setIsFocused(false)}
      className={`relative rounded-2xl border border-slate-200 bg-white p-8 overflow-hidden transition-shadow hover:shadow-lg ${className} `}
    >
      <div
        className="pointer-events-none absolute -inset-px opacity-0 transition duration-300"
        style={{
          opacity: isFocused ? 1 : 0,
          background: `radial-gradient(600px circle at ${position.x}px ${position.y}px, rgba(59, 130, 246, 0.06), transparent 40 %)`,
        }}
      />
      <div className="relative h-full">{children}</div>
    </div>
  )
}

function TypewriterTerminal() {
  const [step, setStep] = useState(0)

  // Robust Async Loop
  useEffect(() => {
    let mounted = true;

    const runAnimation = async () => {
      // Loop forever
      while (mounted) {
        setStep(0);
        await new Promise(r => setTimeout(r, 1000));
        if (mounted) setStep(1);

        await new Promise(r => setTimeout(r, 1500));
        if (mounted) setStep(2);

        await new Promise(r => setTimeout(r, 1500));
        if (mounted) setStep(3);

        await new Promise(r => setTimeout(r, 1500));
        if (mounted) setStep(4);

        // Pause at the end before restarting
        await new Promise(r => setTimeout(r, 5000));
      }
    };

    runAnimation();

    return () => { mounted = false; };
  }, []);

  return (
    <div className="space-y-2 font-mono text-sm">
      <div className="flex items-center gap-2">
        <span className="text-green-400">➜</span>
        <span>git clone https://github.com/arnab2001/Optischema-Slim.git</span>
      </div>

      <div className={`flex items-center gap-2 transition-opacity duration-300 ${step >= 1 ? 'opacity-100' : 'opacity-0'} `}>
        <span className="text-green-400">➜</span>
        <span>docker compose up -d</span>
      </div>

      <div className={`pt-2 text-gray-500 transition-opacity duration-300 ${step >= 2 ? 'opacity-100' : 'opacity-0'} `}>
        [+] Running 3/3<br />
        ✔ Container optischema-db      <span className="text-green-500">Started</span><br />
        ✔ Container optischema-api     <span className="text-green-500">Started</span><br />
      </div>

      <div className={`pt-2 flex items-center gap-2 transition-opacity duration-300 ${step >= 3 ? 'opacity-100' : 'opacity-0'} `}>
        <span className="text-blue-400">ℹ</span>
        <span>Detecting Local LLM...</span>
      </div>

      <div className={`text-emerald-400 pt-1 transition-opacity duration-300 ${step >= 4 ? 'opacity-100' : 'opacity-0'} `}>
        ✔ Connected to Ollama (SQLCoder-7B)
        <br />
        <span className="text-white mt-2 block font-bold">Ready! UI running at http://localhost:3000</span>
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
    if (!email.trim()) return

    setStatus('loading')
    setMessage('')

    try {
      const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'sb_publishable_WrIS4GLRZwLP8LJZi8TjfQ_cCPvoYZQ'
      const response = await fetch('https://lnvkeysarmzdprtmufwt.supabase.co/functions/v1/waitlist', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${anonKey} `,
          'apikey': anonKey,
        },
        body: JSON.stringify({ email: email.trim() }),
      })

      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Failed to join')

      setStatus('success')
      setMessage('You are on the list! Watch your inbox.')
      setEmail('')
    } catch (error) {
      setStatus('error')
      setMessage('Something went wrong. Please try again.')
    }
  }

  return (
    <div className="relative z-10 bg-white rounded-2xl border border-slate-200 p-1 shadow-2xl">
      <div className="bg-white rounded-xl p-8 md:p-12 text-center border border-slate-100 bg-[url('https://grainy-gradients.vercel.app/noise.svg')]">

        <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl mb-8 ring-4 ring-blue-50/50 rotate-3 transition-transform hover:rotate-6">
          <Mail className="w-8 h-8" />
        </div>

        <h2 className="text-2xl font-bold mb-3 text-slate-900">
          Request Early Access
        </h2>
        <p className="text-slate-500 mb-8 max-w-md mx-auto">
          We are polishing the v1 Docker image. Join the waitlist to get the release candidate before we open the repository to the public.
        </p>

        <form onSubmit={handleSubmit} className="max-w-md mx-auto relative">
          <div className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-xl blur opacity-20 group-hover:opacity-40 transition duration-200"></div>
            <div className="relative flex">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="developer@example.com"
                disabled={status === 'loading' || status === 'success'}
                className="w-full pl-5 pr-14 py-4 bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all disabled:opacity-50 font-mono text-sm text-slate-800 shadow-sm"
                required
              />
              <button
                type="submit"
                disabled={status === 'loading' || status === 'success'}
                className="absolute right-2 top-2 bottom-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-slate-400 flex items-center justify-center shadow-md"
              >
                {status === 'loading' ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : status === 'success' ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : (
                  <ArrowRight className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>

          {message && (
            <div className={`mt-4 text-sm font-medium flex items-center justify-center gap-2 animate-fade -in ${status === 'success' ? 'text-green-600' : 'text-red-500'
              } `}>
              {status === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
              {message}
            </div>
          )}
        </form>
      </div>
    </div>
  )
}

export function OptiSchemaLogo() {
  return (
    <div className="flex items-center gap-3 select-none group">
      {/* The Icon: Stylized Postgres Cast Operator */}
      <div className="flex gap-[3px]">
        <div className="w-1.5 h-1.5 bg-blue-600 rounded-sm"></div>
        <div className="w-1.5 h-1.5 bg-blue-600 rounded-sm opacity-50"></div>
        <div className="w-1.5 h-1.5 bg-blue-600 rounded-sm"></div>
        <div className="w-1.5 h-1.5 bg-blue-600 rounded-sm opacity-50"></div>
      </div>

      <div className="flex items-baseline gap-0.5">
        <span className="text-xl font-bold tracking-tight text-slate-900 font-mono">
          OptiSchema
        </span>
        <span className="text-xl font-extrabold text-slate-400 font-mono">
          ::
        </span>
        <span className="text-xl font-bold text-blue-600 font-mono">
          slim
        </span>
      </div>
    </div>

  )
}

function LiveBenchmarkPill() {
  return (
    <div className="relative group cursor-default">
      {/* 1. The Moving Border Gradient (The "Zing") */}
      <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500 via-blue-500 to-emerald-500 rounded-full opacity-30 blur-sm group-hover:opacity-60 transition duration-1000 group-hover:duration-200 animate-gradient-xy"></div>

      {/* 2. The Card Content */}
      <div className="relative flex items-center gap-3 px-4 py-2 bg-white rounded-full leading-none border border-slate-200 shadow-sm">

        {/* Icon with Pulse */}
        <div className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100">
          <Zap className="w-3.5 h-3.5 text-emerald-600 fill-emerald-600 animate-pulse" />
        </div>

        <div className="flex items-center gap-2.5 text-sm">
          <span className="text-slate-500 font-medium">Optimization</span>

          {/* The Data Transformation */}
          <div className="flex items-center gap-2 font-mono">
            <span className="text-slate-400 line-through decoration-red-400/50 decoration-2">
              12.4s
            </span>

            {/* Animated Arrow */}
            <ArrowRight className="w-3 h-3 text-slate-300 group-hover:text-blue-500 group-hover:translate-x-0.5 transition-all" />

            {/* The Result */}
            <span className="text-emerald-600 font-bold bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100">
              50ms
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
