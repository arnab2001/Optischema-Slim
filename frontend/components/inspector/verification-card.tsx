"use client";

import { useAppStore } from "@/store/appStore";
import { ArrowRight, AlertTriangle, CheckCircle, Info, Zap } from "lucide-react";

interface VerificationResult {
    can_simulate: boolean;
    cost_before: number;
    cost_after: number;
    improvement_percent: number;
    index_used: boolean;
    error?: string;
}

interface VerificationCardProps {
    result: VerificationResult;
}

export function VerificationCard({ result }: VerificationCardProps) {
    const { theme } = useAppStore();
    const isDark = theme === "dark";

    if (result.error) {
        return (
            <div className={`mt-4 p-4 rounded-lg border flex items-start gap-3 ${isDark ? "bg-red-900/10 border-red-900/30" : "bg-red-50 border-red-100"
                }`}>
                <AlertTriangle className={`w-4 h-4 mt-0.5 ${isDark ? "text-red-400" : "text-red-600"}`} />
                <div className="flex-1">
                    <p className={`text-xs font-bold uppercase mb-1 ${isDark ? "text-red-400" : "text-red-700"}`}>Simulation Error</p>
                    <p className={`text-sm ${isDark ? "text-slate-300" : "text-slate-700"}`}>{result.error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className={`mt-4 p-4 rounded-xl border animate-in fade-in slide-in-from-top-2 duration-300 ${isDark ? "bg-slate-900 border-slate-700" : "bg-white border-slate-200 shadow-sm"
            }`}>
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-blue-500" />
                    <span className={`text-xs font-bold uppercase tracking-widest ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                        Sandbox Result
                    </span>
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${result.index_used
                        ? "bg-green-500/10 text-green-500 border border-green-500/20"
                        : "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                    }`}>
                    {result.index_used ? "Index Used" : "Index Ignored"}
                </span>
            </div>

            <div className="flex items-center justify-between gap-6">
                <div className="flex items-center gap-4 flex-1">
                    <div className="space-y-1">
                        <div className={`text-[10px] uppercase font-semibold ${isDark ? "text-slate-500" : "text-slate-400"}`}>Baseline</div>
                        <div className={`text-sm font-mono font-medium ${isDark ? "text-slate-300" : "text-slate-700"}`}>
                            {result.cost_before.toFixed(1)}
                        </div>
                    </div>

                    <ArrowRight className={`w-4 h-4 ${isDark ? "text-slate-700" : "text-slate-300"}`} />

                    <div className="space-y-1">
                        <div className={`text-[10px] uppercase font-semibold ${isDark ? "text-slate-500" : "text-slate-400"}`}>Simulated</div>
                        <div className={`text-sm font-mono font-bold ${isDark ? "text-white" : "text-slate-900"}`}>
                            {result.cost_after.toFixed(1)}
                        </div>
                    </div>
                </div>

                <div className="text-right">
                    <div className={`text-[10px] uppercase font-bold mb-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>Improvement</div>
                    <div className={`text-2xl font-black ${result.improvement_percent > 0 ? "text-green-500" : "text-slate-400"}`}>
                        {result.improvement_percent > 0 ? "▼" : ""} {result.improvement_percent.toFixed(1)}%
                    </div>
                </div>
            </div>

            {!result.index_used && (
                <div className={`mt-4 p-3 rounded-lg flex items-start gap-2 ${isDark ? "bg-amber-900/10 border border-amber-900/30" : "bg-amber-50 border border-amber-100"
                    }`}>
                    <Info className={`w-3.5 h-3.5 mt-0.5 ${isDark ? "text-amber-500" : "text-amber-600"}`} />
                    <p className={`text-[11px] leading-relaxed ${isDark ? "text-amber-200/70" : "text-amber-700"}`}>
                        The planner ignored this index. This usually means the table is too small for an index to be faster than a sequential scan, or the query is already optimal.
                    </p>
                </div>
            )}
        </div>
    );
}
