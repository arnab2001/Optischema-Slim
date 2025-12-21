"use client";

import { useAppStore } from "@/store/appStore";
import { useConnectionStore } from "@/store/connectionStore";
import { Zap, Activity, Database, Info } from "lucide-react";
import { useEffect, useState } from "react";

interface MetricStatus {
    value: number | null;
    status: "ok" | "insufficient_data" | "disabled";
}

interface Vitals {
    qps: MetricStatus;
    cache_hit_ratio: MetricStatus;
    active_connections: MetricStatus;
    max_connections: MetricStatus;
}

export function SlimVitals() {
    const { isConnected } = useConnectionStore();
    const { theme, isLiveMode } = useAppStore();
    const isDark = theme === "dark";
    const [vitals, setVitals] = useState<Vitals | null>(null);
    const [loading, setLoading] = useState(false);

    const fetchData = async () => {
        if (!isConnected) return;
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
        try {
            const res = await fetch(`${apiUrl}/api/metrics/vitals`);
            if (res.ok) {
                const data = await res.json();
                setVitals(data);
            }
        } catch (e) {
            console.error("Failed to fetch slim vitals:", e);
        }
    };

    useEffect(() => {
        fetchData();

        // Listen for refresh events
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
    }, [isConnected, isLiveMode]);

    if (!isConnected || !vitals) return null;

    const getCacheColor = (val: number | null) => {
        if (val === null) return "text-slate-400";
        if (val >= 99) return "text-green-500";
        if (val >= 90) return "text-yellow-500";
        return "text-red-500";
    };

    const getConnColor = (active: number, max: number) => {
        const percent = (active / max) * 100;
        if (percent > 80) return "text-red-500";
        if (percent > 50) return "text-yellow-500";
        return "text-green-500";
    };

    return (
        <div className="hidden md:flex items-center gap-6 px-4 py-1.5 rounded-full bg-slate-100/50 dark:bg-slate-800/50 border border-slate-200/50 dark:border-slate-700/50">
            {/* QPS */}
            <div className="flex items-center gap-1.5" title="Queries Per Second">
                <Zap className="w-3.5 h-3.5 text-blue-500" />
                <span className={`text-xs font-bold tabular-nums ${isDark ? "text-slate-200" : "text-slate-700"}`}>
                    {vitals.qps.value?.toFixed(1) || "0.0"}
                </span>
                <span className="text-[10px] font-medium text-slate-500 uppercase">qps</span>
            </div>

            <div className="w-px h-3 bg-slate-300 dark:bg-slate-600" />

            {/* Cache */}
            <div className="flex items-center gap-1.5" title="Cache Hit Ratio">
                <Activity className={`w-3.5 h-3.5 ${getCacheColor(vitals.cache_hit_ratio.value)}`} />
                <span className={`text-xs font-bold tabular-nums ${isDark ? "text-slate-200" : "text-slate-700"}`}>
                    {vitals.cache_hit_ratio.value?.toFixed(1) || "0"}%
                </span>
                <span className="text-[10px] font-medium text-slate-500 uppercase">cache</span>
            </div>

            <div className="w-px h-3 bg-slate-300 dark:bg-slate-600" />

            {/* Connections */}
            <div className="flex items-center gap-1.5" title="Active Connections">
                <Database className={`w-3.5 h-3.5 ${getConnColor(vitals.active_connections.value || 0, vitals.max_connections.value || 100)}`} />
                <span className={`text-xs font-bold tabular-nums ${isDark ? "text-slate-200" : "text-slate-700"}`}>
                    {vitals.active_connections.value}/{vitals.max_connections.value}
                </span>
                <span className="text-[10px] font-medium text-slate-500 uppercase">conn</span>
            </div>
        </div>
    );
}
