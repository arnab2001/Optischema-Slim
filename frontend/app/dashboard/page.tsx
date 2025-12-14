"use client";

import { AppShell } from "@/components/layout/app-shell";
import { useConnectionStore } from "@/store/connectionStore";
import { useEffect, useState } from "react";
import { FilterBar } from "@/components/dashboard/filter-bar";
import { QueryGrid } from "@/components/dashboard/query-grid";
import { InspectorSheet } from "@/components/inspector/inspector-sheet";
import { useAppStore } from "@/store/appStore";
import { QueryMetric } from "@/lib/dashboard-math";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

export default function DashboardPage() {
  const { isConnected } = useConnectionStore();
  const { isLiveMode, setLastUpdated, selectedQueryId, setSelectedQueryId, theme } = useAppStore();
  const isDark = theme === "dark";

  const [metrics, setMetrics] = useState<QueryMetric[]>([]);
  const [filteredMetrics, setFilteredMetrics] = useState<QueryMetric[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [sampleSize, setSampleSize] = useState(50);

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

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

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
  const selectedQuery = metrics.find(m => m.queryid === selectedQueryId);

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className={`text-2xl font-bold ${isDark ? "text-white" : "text-slate-800"}`}>
              Query Impact Explorer
            </h1>
            <p className={`mt-1 text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}>
              Filter and inspect heavy statements. Visual analytics now live in the Analytics tab.
            </p>
          </div>
          <Link
            href="/analytics"
            className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium ${isDark
              ? "bg-slate-800 text-slate-100 border border-slate-700 hover:bg-slate-700"
              : "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50"
              }`}
          >
            Open Analytics
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Filter Bar */}
        <FilterBar
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
          activeFilter={activeFilter}
          onFilterChange={setActiveFilter}
          totalCount={totalCount}
          displayCount={filteredMetrics.length}
          sampleSize={sampleSize}
          onSampleSizeChange={setSampleSize}
          includeSystem={includeSystem}
          onIncludeSystemChange={setIncludeSystem}
          onReset={handleReset}
        />

        {/* Query Grid */}
        <QueryGrid
          metrics={filteredMetrics}
          totalDbTime={totalDbTime}
          loading={loading}
          isConnected={isConnected}
          onRowClick={(queryId) => setSelectedQueryId(queryId)}
        />
      </div>

      {/* Inspector Slide-Over */}
      <InspectorSheet
        query={selectedQuery || null}
        isOpen={!!selectedQueryId}
        onClose={() => setSelectedQueryId(null)}
      />
    </AppShell>
  );
}
