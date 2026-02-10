import type * as React from "react";
import { useState, useEffect, useCallback } from 'react'
import { Copy, ChevronRight, ChevronUp, ChevronDown, AlertTriangle, Filter, Loader2 } from 'lucide-react'
import { Tooltip } from 'react-tooltip'

interface QueryTableProps {
  metrics: any[]
  onDrillDown: (metric: any) => void
  onLoadMore?: () => void
  hasMore?: boolean
  loading?: boolean
}

type SortField = 'time_percentage' | 'mean_time' | 'calls' | 'cache_hit' | 'row_efficiency' | 'efficiency_score'
type FilterType = 'slow' | 'frequent' | 'high_io' | 'all'

function getCacheBadge(percentage: number) {
  if (isNaN(percentage)) return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200">UNKNOWN</span>;
  if (percentage < 90) return (
    <div className="flex gap-1">
      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-red-50 text-red-700 border border-red-200">DISK</span>
      <span className="text-xs text-red-600 font-mono">{percentage.toFixed(0)}%</span>
    </div>
  );
  if (percentage < 99) return (
    <div className="flex gap-1">
      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-yellow-50 text-yellow-700 border border-yellow-200">MIXED</span>
      <span className="text-xs text-yellow-600 font-mono">{percentage.toFixed(0)}%</span>
    </div>
  );
  return (
    <div className="flex gap-1">
      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-50 text-green-700 border border-green-200">RAM</span>
    </div>
  );
}

function getLatencyBadge(ms: number) {
  if (isNaN(ms)) return <span className="bg-gray-200 text-gray-500 px-2 py-0.5 rounded-full text-xs">—</span>;
  if (ms >= 100) return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700 border border-red-200">SLOW</span>;
  if (ms >= 10) return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-50 text-yellow-700 border border-yellow-200">AVG</span>;
  return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700 border border-green-200">FAST</span>;
}

function getRowEfficiencyBadge(eff: number) {
  if (isNaN(eff)) return <span className="bg-gray-200 text-gray-500 px-2 py-0.5 rounded-full text-xs">—</span>;
  if (eff < 50) return <span className="bg-red-100 text-red-800 px-2 py-0.5 rounded-full text-xs">{eff.toFixed(0)}%</span>;
  if (eff < 90) return <span className="bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded-full text-xs">{eff.toFixed(0)}%</span>;
  return <span className="bg-green-100 text-green-800 px-2 py-0.5 rounded-full text-xs">{eff.toFixed(0)}%</span>;
}

function getEfficiencyScoreBadge(score: number) {
  if (isNaN(score)) return <span className="bg-gray-200 text-gray-500 px-2 py-0.5 rounded-full text-xs">—</span>;
  if (score < 50) return <span className="bg-red-100 text-red-800 px-2 py-0.5 rounded-full text-xs">{score.toFixed(0)}%</span>;
  if (score < 80) return <span className="bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded-full text-xs">{score.toFixed(0)}%</span>;
  return <span className="bg-green-100 text-green-800 px-2 py-0.5 rounded-full text-xs">{score.toFixed(0)}%</span>;
}

function msDisplay(ms: number) {
  if (isNaN(ms)) return '—';
  if (ms < 0.01 && ms > 0) return '<0.01 ms';
  return ms.toFixed(2) + ' ms';
}

function getPerformanceScore(metric: any): number {
  // Use backend-calculated performance score if available, otherwise fallback to frontend calculation
  if (metric.performance_score !== undefined && metric.performance_score !== null) {
    return metric.performance_score;
  }

  // Fallback calculation (legacy support)
  let score = 100;

  // Penalize slow queries (mean_time > 10ms)
  if (metric.mean_time > 10) {
    score -= Math.min(40, (metric.mean_time - 10) / 2);
  }

  // Penalize low cache hit rate
  const cacheHit = metric.shared_blks_hit + metric.shared_blks_read > 0
    ? (metric.shared_blks_hit / (metric.shared_blks_hit + metric.shared_blks_read)) * 100
    : 100;
  if (cacheHit < 95) {
    score -= (95 - cacheHit) * 0.5;
  }

  // Penalize high time percentage (queries consuming too much DB time)
  if (metric.time_percentage > 10) {
    score -= Math.min(20, (metric.time_percentage - 10) * 0.5);
  }

  // Bonus for efficient row processing
  const rowEfficiency = metric.rows > 0 && metric.shared_blks_read > 0
    ? Math.min(100, (metric.rows / (metric.shared_blks_read * 8192 / 100)) * 100)
    : 100;
  if (rowEfficiency > 80) {
    score += Math.min(10, (rowEfficiency - 80) * 0.2);
  }

  return Math.max(0, Math.min(100, score));
}

function isSlowQuery(metric: any) {
  return metric.mean_time >= 100;
}

function isFrequentQuery(metric: any) {
  return metric.calls >= 1000;
}

function isHighIOQuery(metric: any) {
  const cache = metric.shared_blks_hit + metric.shared_blks_read > 0 ? (metric.shared_blks_hit / (metric.shared_blks_hit + metric.shared_blks_read)) * 100 : 100;
  return cache < 95;
}

export default function QueryTable({ metrics, onDrillDown, onLoadMore, hasMore = false, loading = false }: QueryTableProps) {
  const [hovered, setHovered] = useState<number | null>(null)
  const [sortField, setSortField] = useState<SortField>('time_percentage')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')
  const [compactMode, setCompactMode] = useState(false)

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return null
    return sortDirection === 'desc' ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />
  }

  // Apply filters
  const filteredMetrics = metrics.filter(metric => {
    switch (activeFilter) {
      case 'slow': return isSlowQuery(metric)
      case 'frequent': return isFrequentQuery(metric)
      case 'high_io': return isHighIOQuery(metric)
      default: return true
    }
  })

  // Sort filtered metrics
  const sorted = [...filteredMetrics].sort((a, b) => {
    let aVal: number, bVal: number

    switch (sortField) {
      case 'cache_hit':
        aVal = a.shared_blks_hit + a.shared_blks_read > 0 ? (a.shared_blks_hit / (a.shared_blks_hit + a.shared_blks_read)) * 100 : 100
        bVal = b.shared_blks_hit + b.shared_blks_read > 0 ? (b.shared_blks_hit / (b.shared_blks_hit + b.shared_blks_read)) * 100 : 100
        break
      case 'row_efficiency':
        aVal = a.rows > 0 && a.shared_blks_read > 0 ? Math.min(100, (a.rows / (a.shared_blks_read * 8192 / 100)) * 100) : 0
        bVal = b.rows > 0 && b.shared_blks_read > 0 ? Math.min(100, (b.rows / (b.shared_blks_read * 8192 / 100)) * 100) : 0
        break
      case 'efficiency_score':
        aVal = getPerformanceScore(a)
        bVal = getPerformanceScore(b)
        break
      default:
        aVal = a[sortField] || 0
        bVal = b[sortField] || 0
    }

    return sortDirection === 'desc' ? bVal - aVal : aVal - bVal
  })

  // Infinite scroll handler
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget
    if (scrollHeight - scrollTop <= clientHeight * 1.5 && hasMore && !loading) {
      onLoadMore?.()
    }
  }, [hasMore, loading, onLoadMore])

  const filters = [
    { key: 'all', label: 'All Queries', count: metrics.length },
    { key: 'slow', label: 'Slow (≥100ms)', count: metrics.filter(isSlowQuery).length },
    { key: 'frequent', label: 'Frequent (≥1k calls)', count: metrics.filter(isFrequentQuery).length },
    { key: 'high_io', label: 'High I/O (<95% cache)', count: metrics.filter(isHighIOQuery).length },
  ]

  return (
    <div className="w-full">
      {/* Filters */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium text-muted-foreground">Filters:</span>
          <div className="flex gap-2">
            {filters.map(filter => (
              <button
                key={filter.key}
                onClick={() => setActiveFilter(filter.key as FilterType)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${activeFilter === filter.key
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
              >
                {filter.label} ({filter.count})
              </button>
            ))}
          </div>
        </div>
        <button
          onClick={() => setCompactMode(!compactMode)}
          className="px-3 py-1 text-xs bg-muted hover:bg-muted/80 rounded-md transition-colors"
        >
          {compactMode ? 'Normal' : 'Compact'} Mode
        </button>
      </div>

      {/* Table */}
      <div className="border border-border rounded-lg overflow-hidden">
        {/* Desktop Table */}
        <div className="hidden md:block">
          <div
            className={`overflow-x-auto ${compactMode ? 'max-h-[600px]' : 'max-h-[500px]'}`}
            onScroll={handleScroll}
          >
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-20">
                <tr className="bg-muted/60 border-b border-border">
                  <th className="sticky left-0 bg-muted/60 z-30 px-3 py-3 text-left font-medium text-foreground">SQL</th>
                  <th
                    className="px-3 py-3 text-right font-medium text-foreground cursor-pointer hover:bg-muted/80 transition-colors"
                    onClick={() => handleSort('time_percentage')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      % Time
                      {getSortIcon('time_percentage')}
                    </div>
                  </th>
                  <th
                    className="px-3 py-3 text-right font-medium text-foreground cursor-pointer hover:bg-muted/80 transition-colors"
                    onClick={() => handleSort('mean_time')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Avg ms
                      {getSortIcon('mean_time')}
                    </div>
                  </th>
                  <th
                    className="px-3 py-3 text-right font-medium text-foreground cursor-pointer hover:bg-muted/80 transition-colors"
                    onClick={() => handleSort('calls')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Calls
                      {getSortIcon('calls')}
                    </div>
                  </th>
                  <th
                    className="px-3 py-3 text-left font-medium text-foreground cursor-pointer hover:bg-muted/80 transition-colors"
                    onClick={() => handleSort('cache_hit')}
                  >
                    <div className="flex items-center gap-1">
                      Cache Hit
                      {getSortIcon('cache_hit')}
                    </div>
                  </th>
                  <th
                    className="px-3 py-3 text-right font-medium text-foreground cursor-pointer hover:bg-muted/80 transition-colors"
                    onClick={() => handleSort('row_efficiency')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Row Eff.
                      {getSortIcon('row_efficiency')}
                    </div>
                  </th>
                  <th
                    className="px-3 py-3 text-right font-medium text-foreground cursor-pointer hover:bg-muted/80 transition-colors"
                    onClick={() => handleSort('efficiency_score')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Efficiency
                      {getSortIcon('efficiency_score')}
                    </div>
                  </th>
                  <th className="px-3 py-3 text-left font-medium text-foreground w-24">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((metric, idx) => {
                  const cache = metric.shared_blks_hit + metric.shared_blks_read > 0 ? (metric.shared_blks_hit / (metric.shared_blks_hit + metric.shared_blks_read)) * 100 : NaN;
                  const eff = metric.rows > 0 && metric.shared_blks_read > 0 ? Math.min(100, (metric.rows / (metric.shared_blks_read * 8192 / 100)) * 100) : NaN;
                  const efficiencyScore = getPerformanceScore(metric);
                  const isSlow = isSlowQuery(metric);

                  return (
                    <tr
                      key={idx}
                      className={`group transition-all duration-200 border-b border-border/50 hover:bg-yellow-50 hover:cursor-pointer ${hovered === idx ? 'bg-yellow-50' : ''
                        } ${compactMode ? 'py-2' : 'py-3'}`}
                      onMouseEnter={() => setHovered(idx)}
                      onMouseLeave={() => setHovered(null)}
                      onClick={() => onDrillDown(metric)}
                    >
                      {/* SQL Snippet */}
                      <td className="sticky left-0 bg-card z-10 px-3 max-w-[320px] whitespace-nowrap overflow-hidden text-ellipsis border-r border-border/50">
                        <div className="flex items-center gap-2">
                          {isSlow && <AlertTriangle className="w-3 h-3 text-red-500 flex-shrink-0" />}
                          <span title={metric.query_text} className="text-foreground flex-1">
                            {metric.query_text?.substring(0, 80)}...
                          </span>
                          <button
                            className="text-xs text-muted-foreground hover:text-primary transition-colors flex-shrink-0"
                            onClick={(e) => {
                              e.stopPropagation()
                              navigator.clipboard.writeText(metric.query_text)
                            }}
                            title="Copy SQL"
                          >
                            <Copy className="w-3 h-3 inline" />
                          </button>
                        </div>
                      </td>
                      {/* % Time Bar */}
                      <td className="px-3 min-w-[120px] text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-[80px] bg-slate-100 rounded h-3 relative overflow-hidden">
                            <div
                              className="absolute right-0 top-0 h-3 rounded bg-primary/80 transition-all duration-300"
                              style={{ width: `${Math.min(100, metric.time_percentage)}%` }}
                            />
                          </div>
                          <span className="text-xs font-mono font-medium text-foreground tabular-nums w-12 text-right">
                            {metric.time_percentage.toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      {/* Avg ms with Latency Badge */}
                      <td className="px-3 text-right">
                        <div className="flex flex-col items-end gap-1">
                          <div className="flex items-center gap-2">
                            {getLatencyBadge(metric.mean_time)}
                            <span className="font-mono font-medium tabular-nums">{msDisplay(metric.mean_time)}</span>
                          </div>
                        </div>
                      </td>
                      {/* Calls */}
                      <td className="px-3 text-right font-mono tabular-nums text-slate-600">{metric.calls.toLocaleString()}</td>
                      {/* Cache Hit % */}
                      <td className="px-3">{getCacheBadge(cache)}</td>
                      {/* Row Efficiency */}
                      <td className="px-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <span className="font-mono tabular-nums text-sm">{eff.toFixed(0)}%</span>
                          <div className="w-16 bg-slate-100 h-1.5 rounded-full overflow-hidden">
                            <div className={`h-full ${eff < 50 ? 'bg-red-500' : 'bg-green-500'}`} style={{ width: `${eff}%` }}></div>
                          </div>
                        </div>
                      </td>
                      {/* Efficiency Score */}
                      <td className="px-3 text-right">
                        <span className={`font-mono font-bold tabular-nums ${efficiencyScore < 50 ? 'text-red-600' : 'text-green-600'}`}>
                          {efficiencyScore.toFixed(0)}
                        </span>
                      </td>
                      {/* Drill-down */}
                      <td className="px-3">
                        <div className="flex items-center justify-center">
                          <button
                            className="text-primary flex items-center gap-1 text-xs font-medium hover:text-primary/80 transition-colors"
                            onClick={(e) => {
                              e.stopPropagation()
                              onDrillDown(metric)
                            }}
                          >
                            Details <ChevronRight className="w-3 h-3" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Mobile Cards */}
        <div className="md:hidden">
          <div className="max-h-[600px] overflow-y-auto" onScroll={handleScroll}>
            <div className="space-y-3 p-4">
              {sorted.map((metric, idx) => {
                const cache = metric.shared_blks_hit + metric.shared_blks_read > 0 ? (metric.shared_blks_hit / (metric.shared_blks_hit + metric.shared_blks_read)) * 100 : NaN;
                const eff = metric.rows > 0 && metric.shared_blks_read > 0 ? Math.min(100, (metric.rows / (metric.shared_blks_read * 8192 / 100)) * 100) : NaN;
                const efficiencyScore = getPerformanceScore(metric);
                const isSlow = isSlowQuery(metric);

                return (
                  <div
                    key={idx}
                    className="bg-card border border-border rounded-lg p-4 cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => onDrillDown(metric)}
                  >
                    {/* Header */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        {isSlow && <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-foreground truncate">
                            {metric.query_text?.substring(0, 60)}...
                          </p>
                        </div>
                      </div>
                      <button
                        className="text-muted-foreground hover:text-primary transition-colors flex-shrink-0 ml-2"
                        onClick={(e) => {
                          e.stopPropagation()
                          navigator.clipboard.writeText(metric.query_text)
                        }}
                        title="Copy SQL"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Metrics Grid */}
                    <div className="grid grid-cols-2 gap-3 mb-3">
                      <div>
                        <p className="text-xs text-muted-foreground">% Time</p>
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-gray-200 rounded h-2 relative">
                            <div
                              className="absolute left-0 top-0 h-2 rounded bg-primary transition-all duration-300"
                              style={{ width: `${Math.min(100, metric.time_percentage)}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium">{metric.time_percentage.toFixed(1)}%</span>
                        </div>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Avg Time</p>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{msDisplay(metric.mean_time)}</span>
                          {getLatencyBadge(metric.mean_time)}
                        </div>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Calls</p>
                        <p className="text-sm font-medium">{metric.calls.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Cache Hit</p>
                        <div className="flex items-center gap-1">
                          {getCacheBadge(cache)}
                        </div>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Row Eff.</p>
                        <div className="flex items-center gap-1">
                          {getRowEfficiencyBadge(eff)}
                        </div>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Efficiency</p>
                        <div className="flex items-center gap-1">
                          {getEfficiencyScoreBadge(efficiencyScore)}
                        </div>
                      </div>
                    </div>

                    {/* Action Button */}
                    <div className="flex justify-end">
                      <button
                        className="text-primary flex items-center gap-1 text-xs font-medium hover:text-primary/80 transition-colors"
                        onClick={(e) => {
                          e.stopPropagation()
                          onDrillDown(metric)
                        }}
                      >
                        View Details <ChevronRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Loading indicator */}
        {loading && (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
            <span className="text-sm text-muted-foreground">Loading more queries...</span>
          </div>
        )}

        {/* Empty state */}
        {sorted.length === 0 && (
          <div className="text-center py-8">
            <p className="text-muted-foreground">
              {activeFilter === 'all'
                ? 'No queries available'
                : 'No queries match current filter; clear to reset.'
              }
            </p>
          </div>
        )}
      </div>
    </div>
  )
} 