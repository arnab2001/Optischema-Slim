"use client";

import { useAppStore } from "@/store/appStore";
import { Activity, Database, Zap, Info } from "lucide-react";
import { useState } from "react";

interface MetricStatus {
    value: number | null;
    status: "ok" | "insufficient_data" | "disabled";
    sample_size?: number;
}

interface Vitals {
    qps: MetricStatus;
    cache_hit_ratio: MetricStatus;
    active_connections: MetricStatus;
    max_connections: MetricStatus;
}

interface VitalsHeaderProps {
    vitals: Vitals | null;
    loading: boolean;
}

export function VitalsHeader({ vitals, loading }: VitalsHeaderProps) {
    const { theme } = useAppStore();
    const isDark = theme === "dark";
    const [hoverIndex, setHoverIndex] = useState<number | null>(null);

    const getDisplayValue = (metric: MetricStatus | undefined, formatter?: (val: number) => string): string => {
        if (!metric) return "—";
        if (metric.status === "insufficient_data") return "— (insufficient data)";
        if (metric.status === "disabled") return "— (disabled)";
        if (metric.value === null || metric.value === undefined) return "—";
        return formatter ? formatter(metric.value) : String(metric.value);
    };

    const getColorForMetric = (metric: MetricStatus | undefined, type: "qps" | "cache" | "connections"): string => {
        if (!metric || metric.status !== "ok") return "slate";

        if (type === "cache") {
            const value = metric.value ?? 0;
            if (value >= 99) return "green";
            if (value >= 90) return "yellow";
            return "red";
        }

        if (type === "connections") {
            const active = vitals?.active_connections?.value ?? 0;
            const max = vitals?.max_connections?.value ?? 100;
            if (max > 0 && (active / max) < 0.8) return "green";
            return "yellow";
        }

        return "blue"; // QPS
    };

    const cards = [
        {
            label: "Queries / Second",
            value: getDisplayValue(vitals?.qps, (val) => val.toFixed(1)),
            icon: Zap,
            color: getColorForMetric(vitals?.qps, "qps"),
            tooltip: vitals?.qps?.status === "disabled"
                ? "pg_stat_statements extension is not enabled. Enable it to track query performance."
                : vitals?.qps?.status === "insufficient_data"
                    ? "Insufficient data to calculate QPS. Wait for more query activity."
                    : "Total query calls from pg_stat_statements divided by database uptime. Represents average queries executed per second since the stats were last reset."
        },
        {
            label: "Cache Hit Ratio",
            value: getDisplayValue(vitals?.cache_hit_ratio, (val) => `${val.toFixed(1)}%`),
            icon: Activity,
            color: getColorForMetric(vitals?.cache_hit_ratio, "cache"),
            tooltip: vitals?.cache_hit_ratio?.status === "insufficient_data"
                ? `Insufficient data (${vitals.cache_hit_ratio.sample_size || 0} total reads). Need at least 1,000 reads for accurate cache hit ratio.`
                : "Percentage of data reads served from PostgreSQL shared_buffers cache vs disk. Target: >99%. Below 90% indicates memory pressure or missing indexes."
        },
        {
            label: "Active Connections",
            value: vitals && vitals.active_connections && vitals.max_connections
                ? `${vitals.active_connections.value}/${vitals.max_connections.value}`
                : "—",
            icon: Database,
            color: getColorForMetric(vitals?.active_connections, "connections"),
            tooltip: "Currently active database connections vs max_connections setting. High usage (>80%) may cause connection pool exhaustion."
        },
    ];

    const getColorClasses = (color: string) => {
        const colors: Record<string, { bg: string; text: string; icon: string }> = {
            blue: {
                bg: isDark ? "bg-blue-900/30" : "bg-blue-50",
                text: isDark ? "text-blue-400" : "text-blue-700",
                icon: isDark ? "text-blue-400" : "text-blue-500",
            },
            green: {
                bg: isDark ? "bg-green-900/30" : "bg-green-50",
                text: isDark ? "text-green-400" : "text-green-700",
                icon: isDark ? "text-green-400" : "text-green-500",
            },
            yellow: {
                bg: isDark ? "bg-yellow-900/30" : "bg-yellow-50",
                text: isDark ? "text-yellow-400" : "text-yellow-700",
                icon: isDark ? "text-yellow-400" : "text-yellow-500",
            },
            red: {
                bg: isDark ? "bg-red-900/30" : "bg-red-50",
                text: isDark ? "text-red-400" : "text-red-700",
                icon: isDark ? "text-red-400" : "text-red-500",
            },
            slate: {
                bg: isDark ? "bg-slate-800" : "bg-slate-100",
                text: isDark ? "text-slate-400" : "text-slate-600",
                icon: isDark ? "text-slate-500" : "text-slate-400",
            },
        };
        return colors[color] || colors.slate;
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {cards.map((card, i) => {
                const colors = getColorClasses(card.color);
                const Icon = card.icon;
                const isConnectionCard = card.label === "Active Connections";
                const activeVal = vitals?.active_connections?.value ?? 0;
                const maxVal = vitals?.max_connections?.value ?? 1;
                const connectionPercent = (activeVal / maxVal) * 100;

                return (
                    <div
                        key={i}
                        className={`rounded-xl border p-4 transition-all ${isDark
                            ? "bg-slate-800/50 border-slate-700/50"
                            : "bg-white border-slate-200"
                            }`}
                    >
                        <div className="flex items-center justify-between">
                            <div className="space-y-1 flex-1">
                                <div className="flex items-center gap-1">
                                    <p className={`text-xs font-medium uppercase tracking-wide ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                        {card.label}
                                    </p>
                                    <span
                                        className="relative cursor-help"
                                        onMouseEnter={() => setHoverIndex(i)}
                                        onMouseLeave={() => setHoverIndex(null)}
                                    >
                                        <Info className={`w-3 h-3 ${isDark ? "text-slate-600" : "text-slate-300"} hover:text-blue-500 transition-colors`} />
                                        {hoverIndex === i && (
                                            <div className={`absolute left-0 top-5 z-10 w-64 text-xs rounded-lg shadow-lg p-3 ${isDark ? "bg-slate-800 text-slate-200 border border-slate-700" : "bg-white text-slate-700 border border-slate-200"}`}>
                                                {card.tooltip}
                                            </div>
                                        )}
                                    </span>
                                </div>
                                {loading ? (
                                    <div className={`h-8 w-24 rounded ${isDark ? "bg-slate-700" : "bg-slate-200"} animate-pulse`} />
                                ) : (
                                    <p className={`text-2xl font-mono font-bold tabular-nums ${colors.text}`}>
                                        {card.value}
                                    </p>
                                )}
                                {/* Progress bar for connections */}
                                {isConnectionCard && !loading && vitals && (
                                    <div className={`mt-2 h-1.5 w-full rounded-full overflow-hidden ${isDark ? "bg-slate-700" : "bg-slate-200"}`}>
                                        <div
                                            className={`h-full rounded-full transition-all ${connectionPercent > 80 ? "bg-red-500" : connectionPercent > 50 ? "bg-yellow-500" : "bg-green-500"
                                                }`}
                                            style={{ width: `${connectionPercent}%` }}
                                        />
                                    </div>
                                )}
                            </div>
                            <div className={`p-3 rounded-xl ${colors.bg}`}>
                                <Icon className={`w-5 h-5 ${colors.icon}`} />
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
