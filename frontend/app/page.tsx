'use client'

import Link from 'next/link'
import Image from 'next/image'
import { useEffect, useMemo, useState } from 'react'

type FAQItem = {
  q: string
  a: string
}

function Navbar() {
  return (
    <div className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Image src="/logo_Opti.png" alt="OptiSchema" width={28} height={28} className="opacity-90" priority />
          <span className="font-semibold tracking-tight">OptiSchema</span>
        </div>
        <nav className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
          <Link href="#docs" className="hover:text-foreground transition-colors">Docs</Link>
          <Link href="#changelog" className="hover:text-foreground transition-colors">Changelog</Link>
          <Link href="#security" className="hover:text-foreground transition-colors">Security</Link>
        </nav>
        <div className="flex items-center gap-2">
          <Link href="/dashboard" className="px-3 py-1.5 rounded-md border hover:bg-accent transition-colors text-sm">Try Sandbox</Link>
          <Link href="/dashboard" className="px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity text-sm">Connect Your DB</Link>
        </div>
      </div>
    </div>
  )
}

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
        <div className="grid lg:grid-cols-2 gap-10 items-center">
          <div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-semibold tracking-tight">
              Find slow SQL, test the fix, apply with confidence.
            </h1>
            <p className="mt-4 text-base sm:text-lg text-muted-foreground max-w-xl">
              OptiSchema watches your workload, pinpoints costly queries, generates executable fixes, and benchmarks them in a safe sandbox—before you touch prod.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Link href="/dashboard" className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity text-sm font-medium">Connect in 60s</Link>
              <Link href="/dashboard" className="px-4 py-2 rounded-md border hover:bg-accent transition-colors text-sm font-medium">Try a live sandbox</Link>
            </div>
            <div className="mt-6 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1">Works with: Postgres • RDS • Aurora</span>
              <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1">Read-only by default</span>
              <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1">No agents</span>
            </div>
          </div>
          <div className="relative">
            <HeroAnimation />
          </div>
        </div>
      </div>
    </section>
  )
}

function HeroAnimation() {
  // Simple sequence: SQL -> plan -> green "Index created" badge -> before/after bars
  return (
    <div className="rounded-xl border p-4 bg-card">
      <div className="grid gap-4">
        <div className="rounded-lg bg-muted p-3 font-mono text-sm overflow-x-auto">
          {`SELECT user_id, COUNT(*) FROM events WHERE created_at > now() - interval '7 days' GROUP BY 1 ORDER BY 2 DESC;`}
        </div>
        <div className="rounded-lg border p-3 text-sm">
          <div className="text-muted-foreground mb-1">EXPLAIN (ANALYZE, BUFFERS)</div>
          <div className="font-mono text-xs leading-relaxed">
            <div>{`Seq Scan on events  (cost=0.00..185423.12 rows=...)`}</div>
            <div>{`Filter: (created_at > now() - '7 days'::interval)`}</div>
            <div>{`Buffers: shared hit=10234 read=5432 dirtied=0`}</div>
          </div>
        </div>
        <div className="flex items-center justify-between">
          <div className="inline-flex items-center gap-2 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-3 py-1 text-xs">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            Index created
          </div>
          <div className="text-xs text-muted-foreground">CREATE INDEX CONCURRENTLY ...</div>
        </div>
        <BeforeAfterBars />
      </div>
    </div>
  )
}

function BeforeAfterBars() {
  const [toggled, setToggled] = useState(false)
  return (
    <div className="rounded-lg border p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-sm font-medium">Latency (ms)</div>
        <button
          onClick={() => setToggled((v) => !v)}
          className="text-xs px-2 py-1 rounded-md border hover:bg-accent transition-colors"
        >
          Toggle Before/After
        </button>
      </div>
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <span className="w-14 text-xs text-muted-foreground">Before</span>
          <div className="h-3 rounded bg-red-500/20 relative w-full overflow-hidden">
            <div
              className={`h-3 bg-red-500/70 rounded transition-all duration-700 ${toggled ? 'w-[35%]' : 'w-[85%]'}`}
            />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="w-14 text-xs text-muted-foreground">After</span>
          <div className="h-3 rounded bg-emerald-500/20 relative w-full overflow-hidden">
            <div
              className={`h-3 bg-emerald-500/70 rounded transition-all duration-700 ${toggled ? 'w-[25%]' : 'w-[65%]'}`}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-8">
      <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight">{title}</h2>
      {subtitle ? <p className="mt-2 text-muted-foreground max-w-2xl">{subtitle}</p> : null}
    </div>
  )
}

function ValueSnapshot() {
  const items = [
    {
      title: 'Real-time hot queries',
      desc: 'Powered by pg_stat_statements to surface inefficient queries as they happen.',
    },
    {
      title: 'AI fixes you can run',
      desc: 'CREATE INDEX CONCURRENTLY, ALTER SYSTEM, and safe query rewrites you can apply.',
    },
    {
      title: 'Sandbox benchmark',
      desc: 'Use a 1% sample or read-replica to validate impact before prod.',
    },
    {
      title: 'One-click apply + rollback + audit',
      desc: 'Apply whitelisted DDL and keep an immutable audit trail.',
    },
  ]
  return (
    <section className="border-t">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <SectionHeader title="Value snapshot" />
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {items.map((it) => (
            <div key={it.title} className="rounded-xl border p-4 bg-card">
              <div className="font-medium">{it.title}</div>
              <div className="text-sm text-muted-foreground mt-2">{it.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function ProblemSolution() {
  return (
    <section className="border-t">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <SectionHeader title="Problem → Solution" />
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="rounded-xl border p-6 bg-card">
            <div className="text-sm uppercase tracking-wider text-muted-foreground mb-2">Problem</div>
            <ul className="list-disc pl-5 space-y-2 text-sm text-muted-foreground">
              <li>Hunting slow queries is noisy</li>
              <li>Plan output is opaque</li>
              <li>Generic advice is vague</li>
              <li>Fixes are risky in prod</li>
            </ul>
          </div>
          <div className="rounded-xl border p-6 bg-card">
            <div className="text-sm uppercase tracking-wider text-muted-foreground mb-2">Solution</div>
            <ul className="list-disc pl-5 space-y-2 text-sm text-muted-foreground">
              <li>Ranked business queries</li>
              <li>Plain-English plan explainers</li>
              <li>Executable SQL fixes</li>
              <li>Safe sandbox and audit trail</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}

function LivePreviewDemo() {
  const [before, setBefore] = useState(420)
  const [after, setAfter] = useState(160)
  const [isReplaying, setIsReplaying] = useState(false)
  const [view, setView] = useState<'before' | 'after' | 'both'>('both')

  const beforeWidth = useMemo(() => Math.min(100, Math.max(10, (before / 600) * 100)), [before])
  const afterWidth = useMemo(() => Math.min(100, Math.max(5, (after / 600) * 100)), [after])

  function replay() {
    setIsReplaying(true)
    // Simple synthetic changes
    const newBefore = 380 + Math.round(Math.random() * 120)
    const newAfter = Math.max(80, Math.round(newBefore * (0.32 + Math.random() * 0.15)))
    setTimeout(() => {
      setBefore(newBefore)
      setAfter(newAfter)
      setIsReplaying(false)
    }, 400)
  }

  return (
    <section className="border-t">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <SectionHeader
          title="Live preview"
          subtitle="Toggle a Before/After benchmark for a sample query. Replay to simulate a sandbox run."
        />
        <div className="grid lg:grid-cols-2 gap-6 items-start">
          <div className="rounded-xl border p-6 bg-card">
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm font-medium">Sample query</div>
              <div className="inline-flex rounded-md border overflow-hidden">
                <button className={`px-3 py-1.5 text-xs ${view === 'before' ? 'bg-accent' : ''}`} onClick={() => setView('before')}>Before</button>
                <button className={`px-3 py-1.5 text-xs ${view === 'after' ? 'bg-accent' : ''}`} onClick={() => setView('after')}>After</button>
                <button className={`px-3 py-1.5 text-xs ${view === 'both' ? 'bg-accent' : ''}`} onClick={() => setView('both')}>Both</button>
              </div>
            </div>
            <div className="font-mono text-sm bg-muted rounded p-3 overflow-x-auto mb-4">
              {`SELECT account_id, sum(amount) FROM payments WHERE status = 'captured' AND created_at >= now() - interval '24 hours' GROUP BY 1;`}
            </div>
            <div className="space-y-3">
              {(view === 'before' || view === 'both') && (
                <div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                    <div className="h-2 w-2 rounded-full bg-red-500/70" /> p95 Before: {before} ms
                  </div>
                  <div className="h-3 bg-red-500/20 rounded overflow-hidden">
                    <div className="h-3 bg-red-500/70 rounded transition-all duration-700" style={{ width: `${beforeWidth}%` }} />
                  </div>
                </div>
              )}
              {(view === 'after' || view === 'both') && (
                <div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                    <div className="h-2 w-2 rounded-full bg-emerald-500/70" /> p95 After: {after} ms
                  </div>
                  <div className="h-3 bg-emerald-500/20 rounded overflow-hidden">
                    <div className="h-3 bg-emerald-500/70 rounded transition-all duration-700" style={{ width: `${afterWidth}%` }} />
                  </div>
                </div>
              )}
            </div>
            <div className="mt-4 flex items-center gap-3">
              <button onClick={replay} disabled={isReplaying} className="px-3 py-1.5 rounded-md border hover:bg-accent transition-colors text-sm disabled:opacity-50">
                {isReplaying ? 'Replaying…' : 'Replay this benchmark'}
              </button>
              <Link href="/dashboard" className="text-sm underline text-muted-foreground hover:text-foreground">Open sandbox</Link>
            </div>
          </div>
          <div className="rounded-xl border p-6 bg-card">
            <MiniQueryTable />
          </div>
        </div>
      </div>
    </section>
  )
}

function MiniQueryTable() {
  const rows = [
    { query: 'SELECT … FROM payments WHERE status = …', pct: 18.2, p95: 420, calls: 2584, cache: 0.92, rowEff: 0.41 },
    { query: 'SELECT … FROM events WHERE created_at > …', pct: 12.7, p95: 310, calls: 8421, cache: 0.88, rowEff: 0.34 },
    { query: 'UPDATE accounts SET …', pct: 9.6, p95: 220, calls: 124, cache: 0.97, rowEff: 0.89 },
  ]
  return (
    <div>
      <div className="text-sm font-medium mb-3">Mini query table</div>
      <div className="rounded-lg border overflow-hidden">
        <div className="grid grid-cols-6 gap-2 bg-muted text-xs px-3 py-2">
          <div className="col-span-3">Query</div>
          <div className="text-right">% time</div>
          <div className="text-right">p95</div>
          <div className="text-right">calls</div>
        </div>
        {rows.map((r, idx) => (
          <div key={idx} className="grid grid-cols-6 gap-2 px-3 py-2 text-xs border-t items-center">
            <div className="col-span-3 truncate font-mono">{r.query}</div>
            <div className="text-right">{r.pct.toFixed(1)}%</div>
            <div className="text-right">{r.p95} ms</div>
            <div className="text-right">{r.calls.toLocaleString()}</div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex items-center gap-3">
        <button className="px-3 py-1.5 rounded-md border hover:bg-accent transition-colors text-sm">Run synthetic demo</button>
        <span className="text-xs text-muted-foreground">Tag: Sampled</span>
      </div>
    </div>
  )
}

function FeaturePillars() {
  const items = [
    {
      title: 'Live Collector',
      code: 'SELECT * FROM pg_stat_statements WHERE total_exec_time DESC LIMIT 50;',
      callout: 'Excludes system queries; low overhead; dedup via fingerprints.',
    },
    {
      title: 'Explain-plan AI',
      code: 'EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT …;\n-- -> CREATE INDEX CONCURRENTLY …',
      callout: 'Heuristics + LLM; outputs SQL patch + rationale + risk; cached.',
    },
    {
      title: 'Sandbox Benchmark',
      code: 'BEGIN; SET LOCAL …; EXPLAIN ANALYZE …; ROLLBACK;',
      callout: 'Temp schema or replica; before/after deltas; I/O tracked.',
    },
    {
      title: 'Apply / Rollback / Audit',
      code: 'CREATE INDEX CONCURRENTLY IF NOT EXISTS …;\n-- audit(event_id, actor, ts, sql)',
      callout: 'Whitelisted DDL; immutable audit log; safe by default.',
    },
  ]
  return (
    <section className="border-t">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <SectionHeader title="Feature pillars" />
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {items.map((it) => (
            <div key={it.title} className="rounded-xl border bg-card overflow-hidden flex flex-col">
              <div className="p-4 border-b font-medium">{it.title}</div>
              <pre className="p-4 text-xs font-mono whitespace-pre-wrap flex-1 bg-muted/40">{it.code}</pre>
              <div className="p-4 text-xs text-muted-foreground border-t">{it.callout}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function HowItWorks() {
  return (
    <section className="border-t" id="docs">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <SectionHeader title="How it works" subtitle="Observe → Analyze → Validate → Ship" />
        <div className="grid lg:grid-cols-2 gap-6 items-center">
          <div>
            <ol className="space-y-4 text-sm">
              <li>
                <span className="font-medium">Observe:</span> pg_stat_statements → rank by total_exec_time
              </li>
              <li>
                <span className="font-medium">Analyze:</span> EXPLAIN (ANALYZE, BUFFERS) → AI suggestion
              </li>
              <li>
                <span className="font-medium">Validate:</span> sandbox benchmark → Δ latency & Δ buffers
              </li>
              <li>
                <span className="font-medium">Ship:</span> apply with rollback + audit trail
              </li>
            </ol>
          </div>
          <div className="rounded-xl border p-4 bg-card">
            <FlowDiagram />
          </div>
        </div>
      </div>
    </section>
  )
}

function FlowDiagram() {
  // Native SVG diagram
  return (
    <svg viewBox="0 0 800 260" className="w-full h-auto">
      <defs>
        <linearGradient id="g1" x1="0" x2="1">
          <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.15" />
          <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.35" />
        </linearGradient>
      </defs>
      {[
        { x: 20, label: 'Observe' },
        { x: 220, label: 'Analyze' },
        { x: 420, label: 'Validate' },
        { x: 620, label: 'Ship' },
      ].map((b, i) => (
        <g key={b.label}>
          <rect x={b.x} y={40} width={160} height={120} rx={14} fill="url(#g1)" stroke="hsl(var(--border))" />
          <text x={b.x + 80} y={80} textAnchor="middle" fontSize="16" fill="currentColor" fontWeight="600">
            {b.label}
          </text>
          <text x={b.x + 80} y={110} textAnchor="middle" fontSize="12" fill="currentColor" opacity="0.7">
            {i === 0 && 'pg_stat_statements'}
            {i === 1 && 'EXPLAIN JSON + AI'}
            {i === 2 && 'Sandbox benchmark'}
            {i === 3 && 'Apply + audit'}
          </text>
        </g>
      ))}
      {[
        { from: 180, to: 220 },
        { from: 380, to: 420 },
        { from: 580, to: 620 },
      ].map((a, idx) => (
        <g key={idx}>
          <line x1={a.from} y1={100} x2={a.to} y2={100} stroke="hsl(var(--border))" strokeWidth={2} />
          <polygon points={`${a.to - 8},94 ${a.to - 8},106 ${a.to},100`} fill="hsl(var(--border))" />
        </g>
      ))}
    </svg>
  )
}

function DeepDive() {
  const items = [
    {
      title: 'Under the hood',
      body:
        'OptiSchema combines engine-side stats (pg_stat_statements), plan analysis (EXPLAIN … JSON), heuristics, and an LLM to produce patches you can apply safely.',
    },
    {
      title: 'Sandbox modes',
      body: '1% sample vs read-replica, with tradeoffs depending on workload and isolation needs.',
    },
    {
      title: 'Latency honesty',
      body: 'DB-engine time only; cross-AZ RTT baseline subtraction for clearer deltas.',
    },
    {
      title: 'Safety model',
      body: 'Read-only creds, whitelisted DDL, audit, idempotent IF (NOT) EXISTS.',
    },
  ]
  const [open, setOpen] = useState<number | null>(0)
  return (
    <section className="border-t">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <SectionHeader title="Deep-dive for engineers" />
        <div className="divide-y rounded-xl border overflow-hidden bg-card">
          {items.map((it, idx) => (
            <div key={it.title}>
              <button
                className="w-full text-left px-4 py-3 hover:bg-accent/50 flex items-center justify-between"
                onClick={() => setOpen(open === idx ? null : idx)}
              >
                <span className="font-medium">{it.title}</span>
                <span className="text-xs text-muted-foreground">{open === idx ? 'Hide' : 'Show'}</span>
              </button>
              {open === idx && <div className="px-4 pb-4 text-sm text-muted-foreground">{it.body}</div>}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function SocialProof() {
  const items = ['–42% top query time', '–65% log-table scan', '<60s to first insight']
  return (
    <section className="border-t">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <SectionHeader title="Results" />
        <div className="grid sm:grid-cols-3 gap-4">
          {items.map((t) => (
            <div key={t} className="rounded-xl border p-6 bg-card text-center text-lg font-semibold">
              {t}
            </div>
          ))}
        </div>
        <div className="mt-6 text-center text-sm text-muted-foreground">Built for: Data teams • Platform • Backend</div>
      </div>
    </section>
  )
}

function SupportedDatabases() {
  const items = [
    { title: 'PostgreSQL (Local)', desc: 'Works out-of-the-box on self-managed instances.' },
    { title: 'Amazon RDS for PostgreSQL', desc: 'Secure by default; read-only creds supported.' },
  ]
  return (
    <section className="border-t">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <SectionHeader title="Supported databases" subtitle="Starting with PostgreSQL—local and RDS. We’re expanding support soon." />
        <div className="grid sm:grid-cols-2 gap-4">
          {items.map((it) => (
            <div key={it.title} className="rounded-xl border p-6 bg-card">
              <div className="text-lg font-semibold">{it.title}</div>
              <div className="mt-2 text-sm text-muted-foreground">{it.desc}</div>
            </div>
          ))}
        </div>
        <div className="mt-6 text-sm text-muted-foreground">
          Coming soon: Aurora Postgres, AlloyDB, and more.
        </div>
      </div>
    </section>
  )
}

function DataFlow() {
  return (
    <section className="border-t">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <SectionHeader
          title="Data collection → Suggestions"
          subtitle="From pg_stat_statements to executable SQL patches with rationale and risk."
        />
        <div className="grid lg:grid-cols-5 gap-6 items-start">
          <div className="lg:col-span-3 rounded-xl border p-4 bg-card">
            <DataFlowDiagram />
          </div>
          <div className="lg:col-span-2 rounded-xl border p-6 bg-card text-sm text-muted-foreground space-y-3">
            <div>
              <div className="text-foreground font-medium">Collect</div>
              <div>Stream hot queries via pg_stat_statements, exclude system noise, fingerprint and dedupe.</div>
            </div>
            <div>
              <div className="text-foreground font-medium">Analyze</div>
              <div>EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) + plan parser + heuristics.</div>
            </div>
            <div>
              <div className="text-foreground font-medium">Suggest</div>
              <div>Rule engine + LLM propose CREATE INDEX CONCURRENTLY / rewrites, with rationale and risk.</div>
            </div>
            <div>
              <div className="text-foreground font-medium">Validate</div>
              <div>Run before/after in a sandbox schema or replica; capture Δ latency & I/O.</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function DataFlowDiagram() {
  const steps = [
    { key: 'collect', label: 'Collect', note: 'pg_stat_statements' },
    { key: 'dedupe', label: 'Fingerprint', note: 'Deduplicate' },
    { key: 'explain', label: 'Explain JSON', note: 'Analyze plan' },
    { key: 'rules', label: 'Heuristics', note: 'Rules engine' },
    { key: 'llm', label: 'LLM', note: 'Rationale + risk' },
    { key: 'suggest', label: 'Suggestion', note: 'SQL patch' },
  ] as const

  const [phase, setPhase] = useState(0)
  const [t, setT] = useState(0)

  // simple animation: cycle steps; move a dot along the active connector
  useEffect(() => {
    const tick = setInterval(() => {
      setT((prev) => {
        const next = prev + 0.08
        if (next >= 1) {
          setPhase((p) => (p + 1) % steps.length)
          return 0
        }
        return next
      })
    }, 120)
    return () => clearInterval(tick)
  }, [])

  const width = 900
  const height = 260
  const boxW = 140
  const boxH = 80
  const startX = 30
  const gap = 25
  const spacing = (width - startX * 2 - boxW) / (steps.length - 1)
  const y = 110

  const positions = steps.map((_, i) => startX + i * spacing)
  const active = phase % steps.length
  const cx1 = positions[Math.max(0, active - 1)] + boxW
  const cx2 = positions[Math.min(steps.length - 1, active)]
  const dotX = active === 0 ? positions[0] : cx1 + (cx2 - cx1) * t
  const dotY = y + boxH / 2

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
      <defs>
        <linearGradient id="nodeBg" x1="0" x2="1">
          <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.10" />
          <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.25" />
        </linearGradient>
      </defs>
      {/* connectors */}
      {positions.slice(0, -1).map((x, i) => (
        <g key={`c-${i}`}>
          <line
            x1={x + boxW}
            y1={y + boxH / 2}
            x2={positions[i + 1]}
            y2={y + boxH / 2}
            stroke="hsl(var(--border))"
            strokeWidth={2}
          />
        </g>
      ))}
      {/* nodes */}
      {steps.map((s, i) => (
        <g key={s.key}>
          <rect
            x={positions[i]}
            y={y}
            width={boxW}
            height={boxH}
            rx={12}
            fill="url(#nodeBg)"
            stroke={i === active ? 'hsl(var(--primary))' : 'hsl(var(--border))'}
            strokeWidth={i === active ? 2.5 : 1.5}
          />
          <text x={positions[i] + boxW / 2} y={y + 32} textAnchor="middle" fontSize="14" fill="currentColor" fontWeight={600}>
            {s.label}
          </text>
          <text x={positions[i] + boxW / 2} y={y + 54} textAnchor="middle" fontSize="11" fill="currentColor" opacity="0.75">
            {s.note}
          </text>
          {i === active && (
            <circle cx={positions[i] + boxW / 2} cy={y - 18} r={4} fill="hsl(var(--primary))" className="animate-pulse" />
          )}
        </g>
      ))}
      {/* flow dot on active connector */}
      {active > 0 && (
        <circle cx={dotX} cy={dotY} r={5} fill="rgb(16,185,129)" opacity={0.9} />
      )}
    </svg>
  )
}

function Pricing() {
  const tiers = [
    {
      name: 'Dev (Free)',
      price: '$0',
      features: ['1 DB', 'Sandbox benchmark', 'AI suggestions (rate-limited)'],
    },
    { name: 'Team', price: '$', features: ['Multi-DB', 'Slack/email digests', 'Audit export', 'RBAC'] },
    { name: 'Enterprise', price: 'Contact', features: ['SSO', 'VPC/private LLM', 'Custom retention', 'Support/SLA'] },
  ]
  return (
    <section className="border-t" id="pricing">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <SectionHeader title="Pricing" />
        <div className="grid md:grid-cols-3 gap-4">
          {tiers.map((t) => (
            <div key={t.name} className="rounded-xl border bg-card p-6 flex flex-col">
              <div className="text-lg font-semibold">{t.name}</div>
              <div className="mt-2 text-2xl">{t.price}</div>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                {t.features.map((f) => (
                  <li key={f} className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary inline-block"></span>
                    {f}
                  </li>
                ))}
              </ul>
              <Link href="/dashboard" className="mt-6 inline-flex justify-center px-3 py-1.5 rounded-md border hover:bg-accent transition-colors text-sm">
                Get started
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Security() {
  const items = [
    'Read-only by default; least privileges needed.',
    'No prod writes during analysis; sandbox is isolated schema/replica.',
    'Configurable model usage/caching; PII-safe mode; data retention knobs.',
  ]
  return (
    <section className="border-t" id="security">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <SectionHeader title="Security & privacy" />
        <div className="grid md:grid-cols-3 gap-4">
          {items.map((t) => (
            <div key={t} className="rounded-xl border p-6 bg-card text-sm text-muted-foreground">
              {t}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function FAQ() {
  const faqs: FAQItem[] = [
    { q: 'Does this add overhead?', a: 'Minimal. We sample stats via pg_stat_statements and exclude system queries.' },
    { q: "What if pg_stat_statements isn’t enabled?", a: 'We detect and help enable with safe defaults; read-only by default.' },
    { q: 'How do you measure latency (network excluded)?', a: 'We rely on engine-side timings and subtract cross-AZ RTT baselines.' },
    { q: 'Can I run it in my VPC?', a: 'Yes. Self-host and/or private LLM options are available.' },
    { q: "What’s the rollback story?", a: 'All DDL is whitelisted; CREATE INDEX CONCURRENTLY and IF (NOT) EXISTS to ensure safety.' },
  ]
  const [open, setOpen] = useState<number | null>(0)
  return (
    <section className="border-t">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <SectionHeader title="FAQ" />
        <div className="divide-y rounded-xl border overflow-hidden bg-card">
          {faqs.map((it, idx) => (
            <div key={it.q}>
              <button
                className="w-full text-left px-4 py-3 hover:bg-accent/50 flex items-center justify-between"
                onClick={() => setOpen(open === idx ? null : idx)}
              >
                <span className="font-medium">{it.q}</span>
                <span className="text-xs text-muted-foreground">{open === idx ? 'Hide' : 'Show'}</span>
              </button>
              {open === idx && <div className="px-4 pb-4 text-sm text-muted-foreground">{it.a}</div>}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function FinalCTA() {
  return (
    <section className="border-t">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <div className="rounded-2xl border p-8 bg-card text-center">
          <div className="text-2xl font-semibold">Prove it on your workload in under a minute.</div>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Link href="/dashboard" className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity text-sm font-medium">Connect your DB</Link>
            <Link href="/dashboard" className="px-4 py-2 rounded-md border hover:bg-accent transition-colors text-sm font-medium">Try sandbox demo</Link>
            <Link href="#docs" className="px-4 py-2 rounded-md border hover:bg-accent transition-colors text-sm font-medium">Read the docs</Link>
          </div>
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-2">
            <EmailCapture />
            <div className="text-xs text-muted-foreground">Privacy-first. Unsubscribe anytime.</div>
          </div>
        </div>
      </div>
    </section>
  )
}

function EmailCapture() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  return (
    <div className="flex items-center gap-2">
      <input
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Get the query-tuning checklist PDF"
        className="px-3 py-2 rounded-md border bg-background text-sm w-64"
      />
      <button
        onClick={() => setSubmitted(true)}
        className="px-3 py-2 rounded-md bg-primary text-primary-foreground text-sm"
      >
        {submitted ? 'Thanks!' : 'Send'}
      </button>
    </div>
  )
}

function Footer() {
  const links = [
    { href: '#docs', label: 'Docs' },
    { href: '#changelog', label: 'Changelog' },
    { href: '#security', label: 'Security' },
    { href: 'https://github.com', label: 'GitHub' },
    { href: '#', label: 'Status' },
    { href: '#', label: 'Contact' },
  ]
  return (
    <footer className="border-t">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10 text-sm">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Image src="/logo_Opti.png" alt="OptiSchema" width={20} height={20} />
            <span>OptiSchema</span>
            <span className="opacity-60">© {new Date().getFullYear()}</span>
          </div>
          <nav className="flex flex-wrap items-center gap-4 text-muted-foreground">
            {links.map((l) => (
              <Link key={l.label} href={l.href} className="hover:text-foreground transition-colors">
                {l.label}
              </Link>
            ))}
          </nav>
        </div>
      </div>
    </footer>
  )
}

export default function Home() {
  return (
    <main className="relative min-h-screen bg-gradient-to-b from-slate-100 via-white to-white dark:from-[hsl(222,20%,8%)] dark:via-[hsl(222,20%,8%)] dark:to-[hsl(222,20%,8%)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(59,130,246,0.14),_transparent_55%)] dark:bg-[radial-gradient(ellipse_at_top_right,_rgba(59,130,246,0.22),_transparent_55%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_rgba(16,185,129,0.10),_transparent_50%)] dark:bg-[radial-gradient(ellipse_at_bottom_left,_rgba(16,185,129,0.16),_transparent_50%)]" />
      <div className="pointer-events-none absolute inset-0 [background-image:linear-gradient(to_right,rgba(100,116,139,0.06)_1px,transparent_1px),linear-gradient(to_bottom,rgba(100,116,139,0.06)_1px,transparent_1px)] [background-size:24px_24px] [mask-image:radial-gradient(ellipse_at_center,black,transparent_70%)] dark:[background-image:linear-gradient(to_right,rgba(148,163,184,0.07)_1px,transparent_1px),linear-gradient(to_bottom,rgba(148,163,184,0.07)_1px,transparent_1px)]" />
      <Navbar />
      <Hero />
      <ValueSnapshot />
      <ProblemSolution />
      <LivePreviewDemo />
      <FeaturePillars />
      <HowItWorks />
      <DeepDive />
      <SocialProof />
      {/* <DataFlow /> */}
      <SupportedDatabases />
      <Security />
      <FAQ />
      <FinalCTA />
      <Footer />
    </main>
  )
}