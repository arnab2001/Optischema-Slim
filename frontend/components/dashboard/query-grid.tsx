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
                        <tr className={`text-xs uppercase tracking-wide ${isDark ? "text-slate-500" : "text-slate-400"
                            }`}>
                            <th className="px-4 py-3 text-left w-1/2">Query</th>
                            <th className="px-4 py-3 text-left w-16">IO</th>
                            <th className="px-4 py-3 text-left w-24">Impact</th>
                            <SortableHeader field="calls" label="Calls" />
                            <SortableHeader field="mean_time" label="Mean (ms)" />
                            <SortableHeader field="total_time" label="Total (ms)" />
                            <th className="px-4 py-3 w-8"></th>
                        </tr>
                    </thead>
                    <tbody className={`divide-y ${isDark ? "divide-slate-700" : "divide-slate-100"}`}>
                        {sortedMetrics.slice(0, 50).map((m, idx) => {
                            const impactPercent = totalDbTime > 0
                                ? (m.total_time / totalDbTime) * 100
                                : 0;

                            return (
                                <tr
                                    key={`${m.queryid}-${idx}`}
                                    onClick={() => onRowClick(m.queryid)}
                                    className={`group cursor-pointer transition-all duration-150 ${isDark
                                        ? "hover:bg-slate-700/70"
                                        : "hover:bg-blue-50/50"
                                        }`}
                                >
                                    <td className="px-4 py-3">
                                        <div
                                            className={`font-mono text-xs truncate max-w-md ${isDark ? "text-slate-300" : "text-slate-700"
                                                }`}
                                            dangerouslySetInnerHTML={{
                                                __html: highlightSQL(m.query.substring(0, 80) + (m.query.length > 80 ? "..." : ""))
                                            }}
                                        />
                                    </td>
                                    <td className="px-4 py-3">
                                        {(() => {
                                            const hits = m.shared_blks_hit || 0;
                                            const reads = m.shared_blks_read || 0;
                                            const total = hits + reads;
                                            const ratio = total > 0 ? (hits / total) * 100 : 0;

                                            let color = "bg-red-500";
                                            if (ratio > 99) color = "bg-green-500";
                                            else if (ratio > 90) color = "bg-yellow-500";

                                            return (
                                                <div className="flex justify-center" title={`Cache Hit Ratio: ${ratio.toFixed(1)}%`}>
                                                    <div className={`w-2.5 h-2.5 rounded-full ${color}`} />
                                                </div>
                                            );
                                        })()}
                                    </td>
                                    <td className="px-4 py-3">
                                        <div className="flex items-center gap-2">
                                            <div className={`w-20 h-2 rounded-full overflow-hidden ${isDark ? "bg-slate-700" : "bg-slate-200"
                                                }`}>
                                                <div
                                                    className={`h-full rounded-full transition-all ${impactPercent > 30
                                                        ? "bg-red-500"
                                                        : impactPercent > 10
                                                            ? "bg-yellow-500"
                                                            : "bg-green-500"
                                                        }`}
                                                    style={{ width: `${Math.min(impactPercent, 100)}%` }}
                                                />
                                            </div>
                                            <span className={`text-xs ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                                {impactPercent.toFixed(1)}%
                                            </span>
                                        </div>
                                    </td>
                                    <td className={`px-4 py-3 text-right tabular-nums ${isDark ? "text-slate-300" : "text-slate-700"
                                        }`}>
                                        {m.calls.toLocaleString()}
                                    </td>
                                    <td className={`px-4 py-3 text-right tabular-nums ${m.mean_time > 500
                                        ? "text-red-500 font-medium"
                                        : isDark ? "text-slate-300" : "text-slate-700"
                                        }`}>
                                        {m.mean_time.toFixed(2)}
                                    </td>
                                    <td className={`px-4 py-3 text-right tabular-nums ${isDark ? "text-slate-300" : "text-slate-700"
                                        }`}>
                                        {m.total_time.toFixed(0).toLocaleString()}
                                    </td>
                                    <td className="px-4 py-3">
                                        <ChevronRight className={`w-4 h-4 transition-all group-hover:translate-x-1 ${isDark
                                            ? "text-slate-600 group-hover:text-slate-300"
                                            : "text-slate-400 group-hover:text-slate-600"
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
