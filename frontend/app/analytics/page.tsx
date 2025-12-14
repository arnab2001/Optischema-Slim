"use client";

import { AppShell } from "@/components/layout/app-shell";
import { VitalsHeader } from "@/components/dashboard/vitals-header";
import { DbInfoPanel } from "@/components/dashboard/db-info-panel";
import { ChartsRow } from "@/components/dashboard/charts-row";
import { HealthScanWidget } from "@/components/HealthScanWidget";
import { useConnectionStore } from "@/store/connectionStore";
import { useAppStore } from "@/store/appStore";
import { QueryMetric } from "@/lib/dashboard-math";
import { useEffect, useState } from "react";
import { Info, RefreshCw } from "lucide-react";

interface Vitals {
  qps: number | null;
  cache_hit_ratio: number | null;
  active_connections: number;
  max_connections: number;
}

const sampleSizes = [10, 25, 50, 100, 200, 500];

export default function AnalyticsPage() {
  const { isConnected } = useConnectionStore();
  const { isLiveMode, setLastUpdated, theme } = useAppStore();
  const isDark = theme === "dark";

  const [metrics, setMetrics] = useState<QueryMetric[]>([]);
  const [vitals, setVitals] = useState<Vitals | null>(null);
  const [loading, setLoading] = useState(false);
  const [sampleSize, setSampleSize] = useState(100);
  const [includeSystem, setIncludeSystem] = useState(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("optischema_show_system_queries");
      return saved === "true";
    }
    return false;
  });

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
  const controlsDisabled = !isConnected || loading;

  const fetchData = async () => {
    if (!isConnected) return;

    setLoading(true);
    try {
      const params = new URLSearchParams({
        sample_size: sampleSize.toString(),
        include_system: includeSystem.toString(),
      });
      const [metricsRes, vitalsRes] = await Promise.all([
        fetch(`${apiUrl}/api/metrics/?${params.toString()}`),
        fetch(`${apiUrl}/api/metrics/vitals`).catch(() => null),
      ]);

      if (metricsRes.ok) {
        const data = await metricsRes.json();
        setMetrics(data.metrics || []);
      }

      if (vitalsRes?.ok) {
        const data = await vitalsRes.json();
        setVitals(data);
      }

      setLastUpdated(new Date());
    } catch (e) {
      console.error("Failed to fetch analytics data:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (!isConnected) return;
    if (!confirm("Reset pg_stat_statements counters? This cannot be undone.")) return;

    try {
      const res = await fetch(`${apiUrl}/api/metrics/reset`, { method: "POST" });
      if (res.ok) {
        fetchData();
      }
    } catch (e) {
      console.error("Failed to reset stats:", e);
    }
  };

  useEffect(() => {
    if (isConnected) {
      fetchData();
    }

    const handleRefresh = () => fetchData();
    window.addEventListener("optischema:refresh", handleRefresh);

    let interval: NodeJS.Timeout | null = null;
    if (isLiveMode && isConnected) {
      interval = setInterval(fetchData, 30000);
    }

    return () => {
      window.removeEventListener("optischema:refresh", handleRefresh);
      if (interval) clearInterval(interval);
    };
  }, [isConnected, isLiveMode, sampleSize, includeSystem]);

  const infoCardClass = `rounded-xl border p-4 ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`;

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header + Controls */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className={`text-2xl font-bold ${isDark ? "text-white" : "text-slate-800"}`}>
              Cumulative X-Ray
            </h1>
            <p className={`mt-1 text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}>
              Visualize where time is spent right now. Metrics are cumulative since the last reset.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={sampleSize}
              onChange={(e) => setSampleSize(Number(e.target.value))}
              className={`text-sm px-3 py-2 rounded-lg border ${isDark
                ? "bg-slate-800 border-slate-700 text-slate-200"
                : "bg-white border-slate-200 text-slate-700"
                }`}
            >
              {sampleSizes.map(size => (
                <option key={size} value={size}>Top {size}</option>
              ))}
            </select>
            <button
              onClick={fetchData}
              disabled={controlsDisabled}
              className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium ${isDark
                ? "bg-slate-800 border-slate-700 text-slate-100 hover:bg-slate-700"
                : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                } ${controlsDisabled ? "opacity-60 cursor-not-allowed" : ""}`}
            >
              <RefreshCw className="w-4 h-4" />
              Sync Now
            </button>
            <button
              onClick={handleReset}
              disabled={controlsDisabled}
              className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium ${isDark
                ? "bg-red-900/30 text-red-200 border border-red-800 hover:bg-red-900/50"
                : "bg-red-50 text-red-600 border border-red-200 hover:bg-red-100"
                } ${controlsDisabled ? "opacity-60 cursor-not-allowed" : ""}`}
            >
              Reset Stats
            </button>
          </div>
        </div>

        {/* Context Banner */}
        <div className={infoCardClass}>
          <div className="flex items-start gap-3">
            <Info className={`w-4 h-4 mt-0.5 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
            <div className="space-y-1 text-sm">
              <p className={isDark ? "text-slate-300" : "text-slate-700"}>
                Showing cumulative pg_stat_statements data since the last reset. Use Reset Stats to start a fresh window.
              </p>
              <p className={isDark ? "text-slate-400" : "text-slate-500"}>
                Charts use the top {sampleSize} statements by total time and refresh every 30s while Live mode is on.
              </p>
            </div>
          </div>
        </div>

        {!isConnected ? (
          <div className={infoCardClass}>
            <p className={isDark ? "text-slate-300" : "text-slate-700"}>
              Connect to a database to view analytics.
            </p>
          </div>
        ) : (
          <>
            <VitalsHeader vitals={vitals} loading={loading} />

            <HealthScanWidget />

            <DbInfoPanel />

            {loading && metrics.length === 0 ? (
              <div className={infoCardClass}>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  <span className={isDark ? "text-slate-300" : "text-slate-600"}>Loading metrics...</span>
                </div>
              </div>
            ) : (
              <ChartsRow metrics={metrics} />
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
