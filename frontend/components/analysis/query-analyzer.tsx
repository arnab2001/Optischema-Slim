"use client";

import { useState } from "react";
import { useConnectionStore } from "@/store/connectionStore";
import { Play, Loader2, CheckCircle2, AlertTriangle, Info, ArrowRight } from "lucide-react";

interface AnalysisResult {
    original_query: string;
    original_cost: number;
    analysis_type: "INDEX" | "REWRITE" | "ADVISORY";
    verification_status: "verified" | "estimated" | "advisory" | "failed";
    suggestion: {
        category: string;
        reasoning: string;
        sql?: string;
        confidence: number;
    };
    simulation?: {
        original_cost: number;
        new_cost: number;
        improvement_percent: number;
        index_sql: string;
        message?: string;
    };
    estimation?: {
        new_cost: number;
        new_sql: string;
        verified: boolean;
    };
    message?: string;
}

export function QueryAnalyzer() {
    const { isConnected } = useConnectionStore();
    const [query, setQuery] = useState("");
    const [analyzing, setAnalyzing] = useState(false);
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleAnalyze = async () => {
        if (!query.trim()) return;

        setAnalyzing(true);
        setError(null);
        setResult(null);

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
            const res = await fetch(`${apiUrl}/api/analysis/analyze`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query }),
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || "Analysis failed");
            }

            setResult(data);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setAnalyzing(false);
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case "verified":
                return (
                    <span className="flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2 py-1 rounded-full border border-green-200">
                        <CheckCircle2 className="w-3 h-3" />
                        Verified
                    </span>
                );
            case "estimated":
                return (
                    <span className="flex items-center gap-1 text-xs font-medium text-yellow-700 bg-yellow-100 px-2 py-1 rounded-full border border-yellow-200">
                        <AlertTriangle className="w-3 h-3" />
                        Estimated
                    </span>
                );
            case "advisory":
                return (
                    <span className="flex items-center gap-1 text-xs font-medium text-blue-700 bg-blue-100 px-2 py-1 rounded-full border border-blue-200">
                        <Info className="w-3 h-3" />
                        Advisory
                    </span>
                );
            default:
                return (
                    <span className="flex items-center gap-1 text-xs font-medium text-red-700 bg-red-100 px-2 py-1 rounded-full border border-red-200">
                        Failed
                    </span>
                );
        }
    };

    return (
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Play className="w-5 h-5 text-slate-500" />
                Query Analyzer
            </h2>

            <div className="space-y-4">
                <div>
                    <textarea
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Paste your SQL query here..."
                        className="w-full h-32 p-3 border border-slate-300 rounded font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-y"
                    />
                </div>

                <button
                    onClick={handleAnalyze}
                    disabled={!isConnected || analyzing || !query.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                    {analyzing ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Analyzing...
                        </>
                    ) : (
                        <>
                            <Play className="w-4 h-4" />
                            Analyze Query
                        </>
                    )}
                </button>

                {error && (
                    <div className="p-4 bg-red-50 text-red-700 rounded border border-red-200 text-sm">
                        {error}
                    </div>
                )}

                {result && (
                    <div className="mt-6 space-y-6 animate-in fade-in slide-in-from-top-4 duration-300">
                        <div className="flex items-center justify-between">
                            <h3 className="font-semibold text-slate-800">Analysis Result</h3>
                            {getStatusBadge(result.verification_status)}
                        </div>

                        <div className="p-4 bg-slate-50 rounded border border-slate-200">
                            <p className="text-sm text-slate-700 mb-2 font-medium">Reasoning:</p>
                            <p className="text-sm text-slate-600 leading-relaxed">
                                {result.suggestion.reasoning}
                            </p>
                        </div>

                        {/* Tier 1: Index Simulation Results */}
                        {result.simulation && (
                            <div className="grid grid-cols-3 gap-4">
                                <div className="p-3 bg-white rounded border border-slate-200 text-center">
                                    <div className="text-xs text-slate-500 uppercase mb-1">Original Cost</div>
                                    <div className="font-mono font-semibold text-slate-700">
                                        {result.simulation.original_cost.toFixed(2)}
                                    </div>
                                </div>
                                <div className="p-3 bg-white rounded border border-slate-200 text-center">
                                    <div className="text-xs text-slate-500 uppercase mb-1">New Cost</div>
                                    <div className="font-mono font-semibold text-green-600">
                                        {result.simulation.new_cost.toFixed(2)}
                                    </div>
                                </div>
                                <div className="p-3 bg-green-50 rounded border border-green-200 text-center">
                                    <div className="text-xs text-green-700 uppercase mb-1">Improvement</div>
                                    <div className="font-bold text-green-700">
                                        {result.simulation.improvement_percent}%
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Tier 2: Rewrite Estimation Results */}
                        {result.estimation && (
                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-3 bg-white rounded border border-slate-200 text-center">
                                    <div className="text-xs text-slate-500 uppercase mb-1">Original Cost</div>
                                    <div className="font-mono font-semibold text-slate-700">
                                        {result.original_cost.toFixed(2)}
                                    </div>
                                </div>
                                <div className="p-3 bg-white rounded border border-slate-200 text-center">
                                    <div className="text-xs text-slate-500 uppercase mb-1">Estimated New Cost</div>
                                    <div className="font-mono font-semibold text-yellow-600">
                                        {result.estimation.new_cost.toFixed(2)}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* SQL Suggestion */}
                        {result.suggestion.sql && (
                            <div>
                                <p className="text-sm text-slate-700 mb-2 font-medium">Suggested SQL:</p>
                                <div className="bg-slate-900 text-slate-50 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                                    <pre>{result.suggestion.sql}</pre>
                                </div>
                            </div>
                        )}

                        {/* Advisory Message */}
                        {result.message && (
                            <div className="p-3 bg-blue-50 text-blue-700 rounded border border-blue-200 text-sm flex items-start gap-2">
                                <Info className="w-4 h-4 mt-0.5 shrink-0" />
                                <span>{result.message}</span>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
