"use client";

import { AppShell } from "@/components/layout/app-shell";
import { useConnectionStore } from "@/store/connectionStore";
import { useEffect, useState } from "react";
// import { FilterBar } from "@/components/dashboard/filter-bar"; 
import { QueryGrid } from "@/components/dashboard/query-grid";
import { InspectorSheet } from "@/components/inspector/inspector-sheet";
import { useAppStore } from "@/store/appStore";
import { QueryMetric } from "@/lib/dashboard-math";
import { ArrowUpRight, Search, X, ChevronDown, ChevronUp } from "lucide-react";
import { ChartsRow } from "@/components/dashboard/charts-row";

export default function DashboardPage() {
  const { isConnected } = useConnectionStore();
  const { isLiveMode, setLastUpdated, selectedQueryId, setSelectedQueryId, theme } = useAppStore();
  const isDark = theme === "dark";

  const [metrics, setMetrics] = useState<QueryMetric[]>([]);
  const [filteredMetrics, setFilteredMetrics] = useState<QueryMetric[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [sampleSize, setSampleSize] = useState(50);
  const [showCharts, setShowCharts] = useState(true);

  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [includeSystem, setIncludeSystem] = useState(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("optischema_show_system_queries");
      return saved === "true";
    }
    return false;
  });

  const apiUrl = import.meta.env.VITE_API_URL || "";

  const fetchData = async () => {
    if (!isConnected) return;

    setLoading(true);
    try {
      const params = new URLSearchParams({
        sample_size: sampleSize.toString(),
        include_system: includeSystem.toString(),
      });
      const metricsRes = await fetch(`${apiUrl}/api/metrics/?${params.toString()}`);

      if (metricsRes.ok) {
        const data = await metricsRes.json();
        setMetrics(data.metrics || []);
        setFilteredMetrics(data.metrics || []);
        setTotalCount(data.total_count || 0);
      }

      setLastUpdated(new Date());
    } catch (e) {
      console.error("Failed to fetch data:", e);
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch and live mode polling
  useEffect(() => {
    if (isConnected) {
      fetchData();
    }

    // Listen for manual refresh from TopBar
    const handleRefresh = () => fetchData();
    window.addEventListener("optischema:refresh", handleRefresh);

    // Live mode polling
    let interval: NodeJS.Timeout | null = null;
    if (isLiveMode && isConnected) {
      interval = setInterval(fetchData, 30000); // 30 second refresh
    }

    return () => {
      window.removeEventListener("optischema:refresh", handleRefresh);
      if (interval) clearInterval(interval);
    };
  }, [isConnected, isLiveMode, sampleSize, includeSystem]);

  // Apply filters
  useEffect(() => {
    let filtered = [...metrics];

    // Search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(m =>
        m.query.toLowerCase().includes(term)
      );
    }

    // Preset filters
    if (activeFilter === "slow") {
      filtered = filtered.filter(m => m.mean_time > 500);
    } else if (activeFilter === "high-freq") {
      filtered = filtered.filter(m => m.calls > 1000);
    } else if (activeFilter === "full-scan") {
      // This would need IO data - approximate by high read ratio
      filtered = filtered.filter(m =>
        m.shared_blks_read && m.shared_blks_hit &&
        m.shared_blks_read > m.shared_blks_hit
      );
    }

    setFilteredMetrics(filtered);
  }, [metrics, searchTerm, activeFilter]);

  // Reset stats
  const handleReset = async () => {
    if (!confirm("Are you sure you want to reset all query statistics? This cannot be undone.")) return;

    try {
      const res = await fetch(`${apiUrl}/api/metrics/reset`, { method: "POST" });
      if (res.ok) {
        fetchData();
      }
    } catch (e) {
      console.error("Failed to reset stats:", e);
    }
  };

  // Calculate total DB time for impact calculation
  const totalDbTime = metrics.reduce((sum, m) => sum + m.total_time, 0);

  // Find selected query for inspector
  const [fetchedQuery, setFetchedQuery] = useState<QueryMetric | null>(null);
  const selectedQuery = metrics.find(m => m.queryid === selectedQueryId);

  // If we have a selectedQueryId but it's not in our current top list (e.g. from Deep Dive),
  // fetch it directly from the backend.
  useEffect(() => {
    if (selectedQueryId && !selectedQuery && fetchedQuery?.queryid !== selectedQueryId) {
      const fetchOne = async () => {
        try {
          const res = await fetch(`${apiUrl}/api/metrics/${selectedQueryId}`);
          if (res.ok) {
            const data = await res.json();
            setFetchedQuery(data);
          }
        } catch (e) {
          console.error("Failed to fetch query detail for deep dive", e);
        }
      };
      fetchOne();
    }
  }, [selectedQueryId, selectedQuery, apiUrl]);

  return (
    <AppShell>
      <div className="space-y-4">
        {/* Charts Row (Collapsible) */}
        <div className={`rounded-xl border overflow-hidden transition-all duration-300 ${isDark ? "bg-slate-800/50 border-slate-700/50" : "bg-white border-slate-200"}`}>
          <button
            onClick={() => setShowCharts(!showCharts)}
            className={`w-full px-4 py-2 flex items-center justify-between text-[10px] uppercase tracking-widest font-bold border-b transition-colors ${isDark ? "border-slate-700/50 hover:bg-slate-700/50 text-slate-400" : "border-slate-100 hover:bg-slate-50 text-slate-500"
              }`}
          >
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
              Workload Analysis
            </div>
            {showCharts ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          <div className={`transition-all duration-500 ease-in-out ${showCharts ? "max-h-[500px] opacity-100 p-3" : "max-h-0 opacity-0"}`}>
            <ChartsRow metrics={metrics} />
          </div>
        </div>

        {/* Dense Header & Filters */}
        <div className={`flex flex-col xl:flex-row xl:items-center justify-between gap-4 p-3 rounded-xl border ${isDark ? "bg-slate-800/50 border-slate-700/50" : "bg-white border-slate-200"}`}>
          {/* Left: Title & Quick Stats */}
          <div className="flex items-center gap-4">
            <div>
              <h1 className={`text-lg font-bold leading-tight ${isDark ? "text-white" : "text-slate-800"}`}>
                Query Impact Explorer
              </h1>
              <div className="flex items-center gap-2 text-xs mt-1">
                <span className={isDark ? "text-slate-400" : "text-slate-500"}>
                  Showing {filteredMetrics.length} / {totalCount} queries
                </span>
                <span className={`${isDark ? "text-slate-600" : "text-slate-300"}`}>|</span>
                <span className={`font-mono tabular-nums ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                  {totalDbTime.toFixed(0)}ms total DB time
                </span>
              </div>
            </div>
          </div>

          {/* Center/Right: Controls */}
          <div className="flex flex-1 flex-col sm:flex-row items-center justify-end gap-3 w-full xl:w-auto">

            {/* Search */}
            <div className="relative w-full sm:w-64 group">
              <Search className={`absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 ${isDark ? "text-slate-500 group-focus-within:text-blue-500" : "text-slate-400 group-focus-within:text-blue-500"} transition-colors`} />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search queries..."
                className={`w-full h-8 pl-8 pr-8 rounded-lg border text-xs font-medium transition-all ${isDark
                  ? "bg-slate-900/50 border-slate-600/50 text-white placeholder:text-slate-600 focus:bg-slate-900 focus:border-blue-500/50"
                  : "bg-slate-50 border-slate-200 text-slate-700 placeholder:text-slate-400 focus:bg-white focus:border-blue-500"
                  } focus:ring-2 focus:ring-blue-500/20 outline-none`}
              />
              {searchTerm && (
                <button onClick={() => setSearchTerm("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            <div className="h-6 w-px bg-slate-200 dark:bg-slate-700 hidden sm:block" />

            {/* Filters */}
            <div className="flex items-center gap-2 overflow-x-auto max-w-full pb-1 sm:pb-0">
              {[
                { id: "slow", label: "Slow (>500ms)", color: "red" },
                { id: "high-freq", label: "Freq (>1k)", color: "orange" },
              ].map(filter => (
                <button
                  key={filter.id}
                  onClick={() => setActiveFilter(activeFilter === filter.id ? null : filter.id)}
                  className={`h-7 px-3 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all ${activeFilter === filter.id
                    ? filter.color === 'red' ? 'bg-red-500 text-white shadow-sm shadow-red-500/20' : 'bg-orange-500 text-white shadow-sm shadow-orange-500/20'
                    : isDark
                      ? 'bg-slate-700/50 text-slate-400 hover:bg-slate-700 border border-slate-600'
                      : 'bg-slate-100 text-slate-500 hover:bg-slate-200 border border-slate-200/50'
                    }`}
                >
                  {filter.label}
                </button>
              ))}

              {/* Controls using native select for compactness */}
              <select
                value={sampleSize}
                onChange={(e) => setSampleSize(Number(e.target.value))}
                className={`h-7 pl-2 pr-6 rounded-md text-xs font-medium border cursor-pointer appearance-none ${isDark ? "bg-slate-700 border-slate-600 text-slate-300" : "bg-white border-slate-200 text-slate-600"
                  }`}
                style={{ backgroundImage: 'none' }}
              >
                {[25, 50, 100].map(s => <option key={s} value={s}>Top {s}</option>)}
              </select>

              <button
                onClick={fetchData}
                className={`h-7 w-7 flex items-center justify-center rounded-md border transition-colors ${isDark ? "bg-slate-700 border-slate-600 text-slate-400 hover:text-white" : "bg-white border-slate-200 text-slate-500 hover:text-blue-600"
                  }`}
                title="Refresh Data"
              >
                <svg className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>

              <button
                onClick={handleReset}
                title="Reset Statistics"
                className={`h-7 px-3 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all border ${isDark
                  ? "bg-red-900/10 border-red-900/30 text-red-400 hover:bg-red-900/20"
                  : "bg-red-50 border-red-100 text-red-600 hover:bg-red-100"
                  }`}
              >
                Reset
              </button>
            </div>
          </div>
        </div>

        {/* Query Grid */}
        <QueryGrid
          metrics={filteredMetrics}
          totalDbTime={totalDbTime}
          loading={loading}
          isConnected={isConnected}
          onRowClick={(queryId) => {
            setFetchedQuery(null); // Clear manual fetch when browsing normally
            setSelectedQueryId(queryId);
          }}
        />
      </div>

      {/* Inspector Slide-Over */}
      <InspectorSheet
        query={selectedQuery || fetchedQuery}
        isOpen={!!selectedQueryId && (!!selectedQuery || !!fetchedQuery)}
        onClose={() => {
          setSelectedQueryId(null);
          setFetchedQuery(null);
        }}
      />
    </AppShell>
  );
}
