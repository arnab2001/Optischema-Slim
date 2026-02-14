"use client";

import { useState, useEffect } from "react";
import { useAppStore } from "@/store/appStore";
import { Zap, DollarSign, RefreshCw, Trash2, TrendingUp } from "lucide-react";
import { toast } from "sonner";

interface TokenStats {
    total_tokens: number;
    total_prompt_tokens: number;
    total_completion_tokens: number;
    total_calls: number;
    by_provider: Record<string, { tokens: number; calls: number }>;
    recent_calls: Array<{
        provider: string;
        model: string;
        prompt_tokens: number;
        completion_tokens: number;
        total_tokens: number;
        created_at: string;
    }>;
}

// Approximate pricing ($ per 1M tokens)
const PRICING: Record<string, { input: number; output: number }> = {
    "gpt-4o-mini": { input: 0.15, output: 0.6 },
    "gpt-4o": { input: 2.5, output: 10 },
    "gpt-4-turbo": { input: 10, output: 30 },
    "gemini-2.0-flash-exp": { input: 0, output: 0 }, // Free tier
    "gemini-1.5-pro": { input: 1.25, output: 5 },
    "deepseek-chat": { input: 0.14, output: 0.28 },
    "deepseek-reasoner": { input: 0.55, output: 2.19 },
    "ollama": { input: 0, output: 0 }, // Self-hosted = free
};

function estimateCost(model: string, promptTokens: number, completionTokens: number): number {
    const pricing = PRICING[model] || PRICING["gpt-4o-mini"]; // Default fallback
    const inputCost = (promptTokens / 1_000_000) * pricing.input;
    const outputCost = (completionTokens / 1_000_000) * pricing.output;
    return inputCost + outputCost;
}

export function TokenUsage() {
    const { theme } = useAppStore();
    const isDark = theme === "dark";
    const [stats, setStats] = useState<TokenStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [resetting, setResetting] = useState(false);

    const apiUrl = import.meta.env.VITE_API_URL || "";

    const fetchStats = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${apiUrl}/api/token-usage`);
            const data = await res.json();
            if (data.success) {
                setStats(data.data);
            }
        } catch (e) {
            toast.error("Failed to fetch token usage");
        } finally {
            setLoading(false);
        }
    };

    const resetStats = async () => {
        if (!confirm("Are you sure you want to reset all token usage counters? This cannot be undone.")) {
            return;
        }

        setResetting(true);
        try {
            const res = await fetch(`${apiUrl}/api/token-usage/reset`, { method: "POST" });
            const data = await res.json();
            if (data.success) {
                toast.success("Token usage reset");
                fetchStats();
            }
        } catch (e) {
            toast.error("Failed to reset counters");
        } finally {
            setResetting(false);
        }
    };

    useEffect(() => {
        fetchStats();
    }, []);

    if (loading) {
        return (
            <div className="flex justify-center py-12">
                <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
            </div>
        );
    }

    if (!stats) {
        return (
            <div className={`text-center py-12 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                No token usage data available
            </div>
        );
    }

    // Estimate total cost across all recent calls
    const totalEstimatedCost = stats.recent_calls.reduce((sum, call) => {
        return sum + estimateCost(call.model, call.prompt_tokens, call.completion_tokens);
    }, 0);

    return (
        <div className="space-y-4">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className={`p-4 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                    <div className="flex items-center gap-2 mb-2">
                        <Zap className="w-4 h-4 text-blue-500" />
                        <span className={`text-xs font-bold uppercase tracking-wider ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                            Total Tokens
                        </span>
                    </div>
                    <div className={`text-2xl font-bold ${isDark ? "text-white" : "text-slate-800"}`}>
                        {stats.total_tokens.toLocaleString()}
                    </div>
                    <div className={`text-xs mt-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                        {stats.total_prompt_tokens.toLocaleString()} in / {stats.total_completion_tokens.toLocaleString()} out
                    </div>
                </div>

                <div className={`p-4 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                    <div className="flex items-center gap-2 mb-2">
                        <TrendingUp className="w-4 h-4 text-green-500" />
                        <span className={`text-xs font-bold uppercase tracking-wider ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                            API Calls
                        </span>
                    </div>
                    <div className={`text-2xl font-bold ${isDark ? "text-white" : "text-slate-800"}`}>
                        {stats.total_calls}
                    </div>
                    <div className={`text-xs mt-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                        {stats.total_calls > 0 ? Math.round(stats.total_tokens / stats.total_calls).toLocaleString() : 0} avg per call
                    </div>
                </div>

                <div className={`p-4 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                    <div className="flex items-center gap-2 mb-2">
                        <DollarSign className="w-4 h-4 text-yellow-500" />
                        <span className={`text-xs font-bold uppercase tracking-wider ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                            Est. Cost
                        </span>
                    </div>
                    <div className={`text-2xl font-bold ${totalEstimatedCost > 1 ? "text-yellow-500" : isDark ? "text-white" : "text-slate-800"}`}>
                        ${totalEstimatedCost.toFixed(4)}
                    </div>
                    <div className={`text-xs mt-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                        Based on recent calls
                    </div>
                </div>
            </div>

            {/* Provider Breakdown */}
            {Object.keys(stats.by_provider).length > 0 && (
                <div className={`p-4 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                    <h3 className={`text-sm font-bold mb-3 ${isDark ? "text-white" : "text-slate-800"}`}>
                        Usage by Provider
                    </h3>
                    <div className="space-y-2">
                        {Object.entries(stats.by_provider).map(([provider, data]) => (
                            <div key={provider} className="flex items-center justify-between">
                                <span className={`text-sm capitalize ${isDark ? "text-slate-300" : "text-slate-700"}`}>
                                    {provider}
                                </span>
                                <div className="flex items-center gap-4">
                                    <span className={`text-xs ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                        {data.tokens.toLocaleString()} tokens
                                    </span>
                                    <span className={`text-xs ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                        {data.calls} calls
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Recent Calls */}
            {stats.recent_calls.length > 0 && (
                <div className={`p-4 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                    <h3 className={`text-sm font-bold mb-3 ${isDark ? "text-white" : "text-slate-800"}`}>
                        Recent Calls
                    </h3>
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                            <thead className={`border-b ${isDark ? "border-slate-700" : "border-slate-200"}`}>
                                <tr className={isDark ? "text-slate-400" : "text-slate-500"}>
                                    <th className="text-left py-2 font-medium">Provider</th>
                                    <th className="text-left py-2 font-medium">Model</th>
                                    <th className="text-right py-2 font-medium">Prompt</th>
                                    <th className="text-right py-2 font-medium">Completion</th>
                                    <th className="text-right py-2 font-medium">Total</th>
                                    <th className="text-right py-2 font-medium">Cost</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-700">
                                {stats.recent_calls.map((call, i) => (
                                    <tr key={i} className={isDark ? "text-slate-300" : "text-slate-700"}>
                                        <td className="py-2 capitalize">{call.provider}</td>
                                        <td className="py-2 font-mono text-xs truncate max-w-[120px]">{call.model}</td>
                                        <td className="py-2 text-right tabular-nums">{call.prompt_tokens.toLocaleString()}</td>
                                        <td className="py-2 text-right tabular-nums">{call.completion_tokens.toLocaleString()}</td>
                                        <td className="py-2 text-right tabular-nums font-bold">{call.total_tokens.toLocaleString()}</td>
                                        <td className="py-2 text-right tabular-nums text-yellow-500">
                                            ${estimateCost(call.model, call.prompt_tokens, call.completion_tokens).toFixed(4)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
                <button
                    onClick={fetchStats}
                    className={`flex-1 py-2 rounded-lg text-sm font-medium border flex items-center justify-center gap-2 ${isDark
                        ? "border-slate-600 text-slate-300 hover:bg-slate-700"
                        : "border-slate-200 text-slate-600 hover:bg-slate-50"
                        }`}
                >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                </button>
                <button
                    onClick={resetStats}
                    disabled={resetting || stats.total_calls === 0}
                    className={`flex-1 py-2 rounded-lg text-sm font-medium border flex items-center justify-center gap-2 disabled:opacity-50 ${isDark
                        ? "border-red-700 text-red-400 hover:bg-red-900/20"
                        : "border-red-200 text-red-600 hover:bg-red-50"
                        }`}
                >
                    {resetting ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                        <Trash2 className="w-4 h-4" />
                    )}
                    Reset Counters
                </button>
            </div>

            {/* Pricing Note */}
            <div className={`p-3 rounded-lg text-xs ${isDark ? "bg-blue-900/20 text-blue-300" : "bg-blue-50 text-blue-700"}`}>
                <strong>Note:</strong> Cost estimates are approximate and based on standard pricing. Ollama (self-hosted) is free. Actual costs may vary by provider and usage tier.
            </div>
        </div>
    );
}
