"use client";

import { useAppStore } from "@/store/appStore";
import { Database, Search, ArrowUpDown, ChevronRight } from "lucide-react";
import { useState } from "react";

interface QueryMetric {
    queryid: string;
    query: string;
    calls: number;
    total_time: number;
    mean_time: number;
    rows: number;
    shared_blks_hit?: number;
    shared_blks_read?: number;
}

interface QueryGridProps {
    metrics: QueryMetric[];
    totalDbTime: number;
    loading: boolean;
    isConnected: boolean;
    onRowClick: (queryId: string) => void;
}

type SortField = "total_time" | "mean_time" | "calls" | "rows";
type SortDir = "asc" | "desc";

export function QueryGrid({
    metrics,
    totalDbTime,
    loading,
    isConnected,
    onRowClick,
}: QueryGridProps) {
    const { theme } = useAppStore();
    const isDark = theme === "dark";

    const [sortField, setSortField] = useState<SortField>("total_time");
    const [sortDir, setSortDir] = useState<SortDir>("desc");

    // Sort metrics
    const sortedMetrics = [...metrics].sort((a, b) => {
        const aVal = a[sortField];
        const bVal = b[sortField];
        return sortDir === "desc" ? bVal - aVal : aVal - bVal;
    });

    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortDir(sortDir === "desc" ? "asc" : "desc");
        } else {
            setSortField(field);
            setSortDir("desc");
        }
    };

    // Highlight SQL keywords
    const highlightSQL = (sql: string) => {
        const keywords = ["SELECT", "FROM", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "ON", "AND", "OR", "ORDER BY", "GROUP BY", "LIMIT", "INSERT", "UPDATE", "DELETE"];
        let highlighted = sql;
        keywords.forEach(kw => {
            const regex = new RegExp(`\\b${kw}\\b`, "gi");
            highlighted = highlighted.replace(regex, `<span class="text-blue-500 font-semibold">${kw}</span>`);
        });
        return highlighted;
    };

    if (!isConnected) {
        return (
            <div className={`rounded-xl border p-12 text-center ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"
                }`}>
                <Database className={`w-12 h-12 mx-auto mb-4 ${isDark ? "text-slate-600" : "text-slate-300"}`} />
                <p className={isDark ? "text-slate-400" : "text-slate-500"}>
                    Connect to a database to view query metrics
                </p>
            </div>
        );
    }

    if (loading && metrics.length === 0) {
        return (
            <div className={`rounded-xl border p-12 ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"
                }`}>
                <div className="flex items-center justify-center gap-3">
                    <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    <span className={isDark ? "text-slate-400" : "text-slate-500"}>Loading metrics...</span>
                </div>
            </div>
        );
    }

    if (metrics.length === 0) {
        return (
            <div className={`rounded-xl border p-12 text-center ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"
                }`}>
                <Search className={`w-12 h-12 mx-auto mb-4 ${isDark ? "text-slate-600" : "text-slate-300"}`} />
                <p className={isDark ? "text-slate-400" : "text-slate-500"}>
                    No queries found matching your filters
                </p>
            </div>
        );
    }

    const SortableHeader = ({ field, label }: { field: SortField; label: string }) => (
        <th
            onClick={() => handleSort(field)}
            className={`px-4 py-3 text-right cursor-pointer hover:bg-opacity-50 ${sortField === field
                ? isDark ? "text-blue-400" : "text-blue-600"
                : ""
                }`}
        >
            <div className="flex items-center justify-end gap-1">
                {label}
                <ArrowUpDown className="w-3 h-3" />
            </div>
        </th>
    );

    return (
        <div className={`rounded-xl border overflow-hidden ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"
            }`}>
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead className={isDark ? "bg-slate-900" : "bg-slate-50"}>
                        <tr className={`text-[10px] uppercase tracking-widest font-bold ${isDark ? "text-slate-500 border-b border-slate-700" : "text-slate-400 border-b border-slate-100"
                            }`}>
                            <th className="px-6 py-4 text-left">Query Source</th>
                            <th className="px-6 py-4 text-center w-16">Health</th>
                            <th className="px-6 py-4 text-left w-48">Resource Impact (%)</th>
                            <SortableHeader field="calls" label="Calls" />
                            <SortableHeader field="mean_time" label="Latency" />
                            <SortableHeader field="total_time" label="Total Time" />
                            <th className="px-6 py-4 w-8"></th>
                        </tr>
                    </thead>
                    <tbody className={`divide-y ${isDark ? "divide-slate-700/50" : "divide-slate-100"}`}>
                        {sortedMetrics.map((m, idx) => {
                            const impactPercent = totalDbTime > 0
                                ? (m.total_time / totalDbTime) * 100
                                : 0;

                            return (
                                <tr
                                    key={`${m.queryid}-${idx}`}
                                    onClick={() => onRowClick(m.queryid)}
                                    className={`group cursor-pointer transition-all duration-150 ${isDark
                                        ? "hover:bg-slate-700/50"
                                        : "hover:bg-blue-50/40"
                                        }`}
                                >
                                    <td className="px-6 py-5">
                                        <div
                                            className={`font-mono text-[11px] truncate max-w-lg ${isDark ? "text-slate-200" : "text-slate-800"
                                                }`}
                                            dangerouslySetInnerHTML={{
                                                __html: highlightSQL(m.query.substring(0, 100) + (m.query.length > 100 ? "..." : ""))
                                            }}
                                        />
                                    </td>
                                    <td className="px-6 py-5">
                                        {(() => {
                                            const hits = m.shared_blks_hit || 0;
                                            const reads = m.shared_blks_read || 0;
                                            const total = hits + reads;
                                            const ratio = total > 0 ? (hits / total) * 100 : 0;

                                            let color = "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]";
                                            if (ratio > 99) color = "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.3)]";
                                            else if (ratio > 90) color = "bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.3)]";

                                            return (
                                                <div className="flex justify-center" title={`Cache Hit Ratio: ${ratio.toFixed(1)}%`}>
                                                    <div className={`w-2 h-2 rounded-full ${color}`} />
                                                </div>
                                            );
                                        })()}
                                    </td>
                                    <td className="px-6 py-5">
                                        <div className="flex items-center gap-3">
                                            <div className={`flex-1 h-1.5 rounded-full overflow-hidden ${isDark ? "bg-slate-700" : "bg-slate-100"
                                                }`}>
                                                <div
                                                    className={`h-full rounded-full transition-all duration-1000 ${impactPercent > 20
                                                        ? "bg-red-500"
                                                        : impactPercent > 5
                                                            ? "bg-amber-500"
                                                            : "bg-blue-500"
                                                        }`}
                                                    style={{ width: `${Math.min(impactPercent, 100)}%` }}
                                                />
                                            </div>
                                            <span className={`text-[10px] font-bold min-w-[32px] ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                                {impactPercent.toFixed(1)}%
                                            </span>
                                        </div>
                                    </td>
                                    <td className={`px-6 py-5 text-right tabular-nums text-xs ${isDark ? "text-slate-300" : "text-slate-600"
                                        }`}>
                                        {m.calls.toLocaleString()}
                                    </td>
                                    <td className={`px-6 py-5 text-right tabular-nums text-xs ${m.mean_time > 500
                                        ? "text-red-500 font-bold"
                                        : isDark ? "text-slate-300" : "text-slate-600"
                                        }`}>
                                        {m.mean_time.toFixed(1)}ms
                                    </td>
                                    <td className={`px-6 py-5 text-right tabular-nums text-xs font-semibold ${isDark ? "text-slate-200" : "text-slate-900"
                                        }`}>
                                        {m.total_time.toFixed(0).toLocaleString()}ms
                                    </td>
                                    <td className="px-6 py-5">
                                        <ChevronRight className={`w-4 h-4 transition-all group-hover:translate-x-1 ${isDark
                                            ? "text-slate-600 group-hover:text-blue-400"
                                            : "text-slate-300 group-hover:text-blue-600"
                                            }`} />
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
