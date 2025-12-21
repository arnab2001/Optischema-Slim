"use client";

import { useAppStore } from "@/store/appStore";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
    Legend
} from "recharts";
import { calculateDashboardStats, QueryMetric } from "@/lib/dashboard-math";
import { useMemo } from "react";

interface ChartsRowProps {
    metrics: QueryMetric[];
}

export function ChartsRow({ metrics }: ChartsRowProps) {
    const { theme } = useAppStore();
    const isDark = theme === "dark";

    const stats = useMemo(() => calculateDashboardStats(metrics), [metrics]);

    const cardClass = `p-4 rounded-xl border ${isDark
        ? "bg-slate-800 border-slate-700"
        : "bg-white border-slate-200"}`;

    const textClass = isDark ? "text-slate-400" : "text-slate-500";
    const titleClass = `text-sm font-medium mb-4 ${isDark ? "text-slate-300" : "text-slate-700"}`;

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Chart A: Latency Buckets */}
            <div className={cardClass}>
                <h3 className={titleClass}>Latency Distribution</h3>
                <div className="h-48 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={stats.latencyHistogram}>
                            <CartesianGrid strokeDasharray="3 3" stroke={isDark ? "#334155" : "#e2e8f0"} vertical={false} />
                            <XAxis
                                dataKey="label"
                                stroke={isDark ? "#94a3b8" : "#64748b"}
                                fontSize={10}
                                tickLine={false}
                                axisLine={false}
                            />
                            <YAxis
                                stroke={isDark ? "#94a3b8" : "#64748b"}
                                fontSize={10}
                                tickLine={false}
                                axisLine={false}
                            />
                            <Tooltip
                                cursor={{ fill: isDark ? "#334155" : "#f1f5f9" }}
                                contentStyle={{
                                    backgroundColor: isDark ? "#1e293b" : "#fff",
                                    borderColor: isDark ? "#334155" : "#e2e8f0",
                                    color: isDark ? "#f8fafc" : "#0f172a",
                                    fontSize: "12px"
                                }}
                            />
                            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                                {stats.latencyHistogram.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.fill} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Chart B: Load Split */}
            <div className={cardClass}>
                <h3 className={titleClass}>Load Split (Read vs Write)</h3>
                <div className="h-48 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={stats.loadSplit}
                                cx="50%"
                                cy="50%"
                                innerRadius={40}
                                outerRadius={70}
                                paddingAngle={5}
                                dataKey="value"
                            >
                                {stats.loadSplit.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.fill} />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: isDark ? "#1e293b" : "#fff",
                                    borderColor: isDark ? "#334155" : "#e2e8f0",
                                    color: isDark ? "#f8fafc" : "#0f172a",
                                    fontSize: "12px"
                                }}
                            />
                            <Legend
                                verticalAlign="bottom"
                                height={36}
                                iconType="circle"
                                formatter={(value) => <span className={`text-xs ${textClass}`}>{value}</span>}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Chart C: Time Consumed */}
            <div className={cardClass}>
                <h3 className={titleClass}>Top Tables by Time</h3>
                <div className="h-48 w-full overflow-y-auto pr-2">
                    {stats.timeConsumed.length > 0 ? (
                        <div className="space-y-3">
                            {(() => {
                                const maxVal = Math.max(...stats.timeConsumed.map(d => d.value));
                                return stats.timeConsumed.map((item, i) => (
                                    <div key={i} className="w-full">
                                        <div className="flex justify-between text-xs mb-1">
                                            <span className={`font-medium ${isDark ? "text-slate-300" : "text-slate-700"}`}>
                                                {item.name}
                                            </span>
                                            <span className={`font-mono ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                                {item.value.toFixed(2)}ms
                                            </span>
                                        </div>
                                        <div className={`w-full h-2 rounded-full ${isDark ? "bg-slate-700" : "bg-slate-100"}`}>
                                            <div
                                                className="h-full rounded-full bg-violet-500 transition-all duration-500"
                                                style={{ width: `${(item.value / maxVal) * 100}%` }}
                                            />
                                        </div>
                                    </div>
                                ));
                            })()}
                        </div>
                    ) : (
                        <div className="h-full flex items-center justify-center text-xs text-slate-500">
                            No table data available
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
