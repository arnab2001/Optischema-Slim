"use client";

import { useAppStore } from "@/store/appStore";
import { X, Copy, ExternalLink, Code, BarChart3, Table2, Zap, Info } from "lucide-react";
import { useState, useEffect } from "react";
import { toast } from "sonner";

interface QueryMetric {
    queryid: string;
    query: string;
    calls: number;
    total_time: number;
    mean_time: number;
    rows: number;
}

interface InspectorSheetProps {
    query: QueryMetric | null;
    isOpen: boolean;
    onClose: () => void;
}

type Tab = "sql" | "plan" | "stats";

export function InspectorSheet({ query, isOpen, onClose }: InspectorSheetProps) {
    const { theme } = useAppStore();
    const isDark = theme === "dark";
    const [activeTab, setActiveTab] = useState<Tab>("sql");
    const [analyzing, setAnalyzing] = useState(false);
    const [analysisResult, setAnalysisResult] = useState<any>(null);
    const [analysisError, setAnalysisError] = useState<{
        message: string;
        suggestion?: string;
        statement_type?: string;
    } | null>(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

    // Reset state when query changes
    useEffect(() => {
        setAnalysisResult(null);
        setAnalysisError(null);
        setActiveTab("sql");
    }, [query?.queryid]);

    // Handle escape key
    useEffect(() => {
        const handleEsc = (e: KeyboardEvent) => {
            if (e.key === "Escape") onClose();
        };
        window.addEventListener("keydown", handleEsc);
        return () => window.removeEventListener("keydown", handleEsc);
    }, [onClose]);

    const copyToClipboard = (text: string, label: string) => {
        navigator.clipboard.writeText(text);
        toast.success(`${label} copied to clipboard`);
    };

    const formatSQL = (sql: string) => {
        // Basic SQL formatting
        const keywords = ["SELECT", "FROM", "WHERE", "JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "ON", "AND", "OR", "ORDER BY", "GROUP BY", "HAVING", "LIMIT", "OFFSET", "INSERT INTO", "VALUES", "UPDATE", "SET", "DELETE FROM"];
        let formatted = sql;
        keywords.forEach(kw => {
            formatted = formatted.replace(new RegExp(`\\b${kw}\\b`, "gi"), `\n${kw}`);
        });
        return formatted.trim();
    };

    const runAnalysis = async () => {
        if (!query) return;

        setAnalyzing(true);
        setAnalysisError(null);
        setAnalysisResult(null);
        
        try {
            const res = await fetch(`${apiUrl}/api/analysis/analyze`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: query.query }),
            });

            if (res.ok) {
                const data = await res.json();
                setAnalysisResult(data);
                toast.success("Analysis complete");
            } else {
                const errorData = await res.json().catch(() => ({ detail: "Analysis failed" }));
                const detail = errorData.detail || {};
                
                // Handle structured error response
                if (typeof detail === "object" && detail.message) {
                    setAnalysisError({
                        message: detail.message,
                        suggestion: detail.suggestion,
                        statement_type: detail.statement_type
                    });
                } else {
                    setAnalysisError({
                        message: typeof detail === "string" ? detail : "Analysis failed",
                        suggestion: "Please check your query syntax and try again."
                    });
                }
            }
        } catch (e) {
            setAnalysisError({
                message: "Failed to analyze query",
                suggestion: "Please check your network connection and try again."
            });
        } finally {
            setAnalyzing(false);
        }
    };

    if (!isOpen || !query) return null;

    const tabs = [
        { id: "sql" as Tab, label: "SQL", icon: Code },
        { id: "plan" as Tab, label: "Plan", icon: BarChart3 },
        { id: "stats" as Tab, label: "Stats", icon: Table2 },
    ];

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 transition-opacity"
                onClick={onClose}
            />

            {/* Sheet */}
            <div className={`fixed right-0 top-0 h-full w-full max-w-2xl z-50 shadow-2xl transform transition-transform duration-300 ${isOpen ? "translate-x-0" : "translate-x-full"
                } ${isDark ? "bg-slate-900" : "bg-white"}`}>
                {/* Header */}
                <div className={`h-14 flex items-center justify-between px-6 border-b ${isDark ? "border-slate-700" : "border-slate-200"
                    }`}>
                    <div className="flex items-center gap-3">
                        <span className={`font-mono text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                            #{query.queryid.substring(0, 8)}
                        </span>
                        <button
                            onClick={() => copyToClipboard(window.location.href, "Link")}
                            className={`p-1.5 rounded hover:bg-opacity-10 ${isDark ? "text-slate-400 hover:bg-white" : "text-slate-500 hover:bg-black"
                                }`}
                            title="Copy link"
                        >
                            <ExternalLink className="w-4 h-4" />
                        </button>
                    </div>
                    <button
                        onClick={onClose}
                        className={`p-2 rounded-lg ${isDark ? "text-slate-400 hover:bg-slate-800" : "text-slate-500 hover:bg-slate-100"
                            }`}
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Tabs */}
                <div className={`flex border-b ${isDark ? "border-slate-700" : "border-slate-200"}`}>
                    {tabs.map((tab) => {
                        const Icon = tab.icon;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === tab.id
                                    ? `border-blue-500 ${isDark ? "text-white" : "text-blue-600"}`
                                    : `border-transparent ${isDark ? "text-slate-500 hover:text-slate-300" : "text-slate-500 hover:text-slate-700"}`
                                    }`}
                            >
                                <Icon className="w-4 h-4" />
                                {tab.label}
                            </button>
                        );
                    })}
                </div>

                {/* Content */}
                <div className="flex-1 overflow-auto p-6" style={{ height: "calc(100% - 112px)" }}>
                    {activeTab === "sql" && (
                        <div className="space-y-4">
                            {/* SQL Block */}
                            <div className={`rounded-lg overflow-hidden ${isDark ? "bg-slate-800" : "bg-slate-900"
                                }`}>
                                <div className="flex items-center justify-between px-4 py-2 bg-opacity-50">
                                    <span className="text-xs font-medium text-slate-500">SQL Query</span>
                                    <button
                                        onClick={() => copyToClipboard(query.query, "SQL")}
                                        className="text-xs text-blue-500 hover:text-blue-400 flex items-center gap-1"
                                    >
                                        <Copy className="w-3 h-3" />
                                        Copy
                                    </button>
                                </div>
                                <pre className="p-4 text-sm text-slate-200 font-mono overflow-x-auto whitespace-pre-wrap">
                                    {formatSQL(query.query)}
                                </pre>
                            </div>

                            {/* Quick Stats */}
                            <div className="grid grid-cols-3 gap-4">
                                <div className={`p-4 rounded-lg ${isDark ? "bg-slate-800" : "bg-slate-50"}`}>
                                    <div className={`text-xs uppercase ${isDark ? "text-slate-500" : "text-slate-400"}`}>Calls</div>
                                    <div className={`text-xl font-bold ${isDark ? "text-white" : "text-slate-800"}`}>
                                        {query.calls.toLocaleString()}
                                    </div>
                                </div>
                                <div className={`p-4 rounded-lg ${isDark ? "bg-slate-800" : "bg-slate-50"}`}>
                                    <div className={`text-xs uppercase ${isDark ? "text-slate-500" : "text-slate-400"}`}>Mean Time</div>
                                    <div className={`text-xl font-bold ${query.mean_time > 500 ? "text-red-500" : isDark ? "text-white" : "text-slate-800"}`}>
                                        {query.mean_time.toFixed(2)} ms
                                    </div>
                                </div>
                                <div className={`p-4 rounded-lg ${isDark ? "bg-slate-800" : "bg-slate-50"}`}>
                                    <div className={`text-xs uppercase ${isDark ? "text-slate-500" : "text-slate-400"}`}>Total Time</div>
                                    <div className={`text-xl font-bold ${isDark ? "text-white" : "text-slate-800"}`}>
                                        {query.total_time.toFixed(0)} ms
                                    </div>
                                </div>
                            </div>

                            {/* Statement Type Badge (if unsupported) */}
                            {analysisError?.statement_type && (
                                <div className={`px-3 py-2 rounded-lg border ${isDark ? "bg-yellow-900/20 border-yellow-700/50" : "bg-yellow-50 border-yellow-200"}`}>
                                    <div className="flex items-center gap-2">
                                        <Info className={`w-4 h-4 ${isDark ? "text-yellow-400" : "text-yellow-600"}`} />
                                        <span className={`text-sm font-medium ${isDark ? "text-yellow-400" : "text-yellow-700"}`}>
                                            {analysisError.statement_type} Statement
                                        </span>
                                    </div>
                                </div>
                            )}

                            {/* Analyze Button */}
                            <button
                                onClick={runAnalysis}
                                disabled={analyzing}
                                className={`w-full py-3 rounded-lg font-medium flex items-center justify-center gap-2 disabled:opacity-50 ${
                                    analysisError
                                        ? isDark
                                            ? "bg-yellow-600 hover:bg-yellow-700 text-white"
                                            : "bg-yellow-600 hover:bg-yellow-700 text-white"
                                        : "bg-blue-600 hover:bg-blue-700 text-white"
                                }`}
                            >
                                {analyzing ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                        Analyzing...
                                    </>
                                ) : (
                                    <>
                                        <Zap className="w-4 h-4" />
                                        {analysisError ? "Retry Analysis" : "Analyze Query"}
                                    </>
                                )}
                            </button>

                            {/* Analysis Error Display */}
                            {analysisError && (
                                <div className={`mt-4 p-4 rounded-lg border ${isDark ? "bg-red-900/20 border-red-700/50" : "bg-red-50 border-red-200"}`}>
                                    <div className="flex items-start gap-3">
                                        <div className={`flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center ${isDark ? "bg-red-800" : "bg-red-100"}`}>
                                            <X className={`w-3 h-3 ${isDark ? "text-red-400" : "text-red-600"}`} />
                                        </div>
                                        <div className="flex-1 space-y-2">
                                            <p className={`text-sm font-medium ${isDark ? "text-red-400" : "text-red-700"}`}>
                                                {analysisError.message}
                                            </p>
                                            {analysisError.suggestion && (
                                                <div className={`flex items-start gap-2 p-2 rounded ${isDark ? "bg-slate-800/50" : "bg-white"}`}>
                                                    <Info className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                                    <p className={`text-xs ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                                                        {analysisError.suggestion}
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Analysis Result */}
                            {analysisResult && (
                                <div className={`mt-6 p-4 rounded-lg border ${isDark ? "bg-slate-800 border-slate-700" : "bg-slate-50 border-slate-200"
                                    }`}>
                                    <div className="flex items-center gap-2 mb-3">
                                        <span className={`px-2 py-1 rounded text-xs font-medium ${analysisResult.verification_status === "verified"
                                            ? "bg-green-100 text-green-700"
                                            : analysisResult.verification_status === "estimated"
                                                ? "bg-yellow-100 text-yellow-700"
                                                : "bg-blue-100 text-blue-700"
                                            }`}>
                                            {analysisResult.verification_status?.toUpperCase()}
                                        </span>
                                        <div className="relative group">
                                            <Info className={`w-3.5 h-3.5 cursor-help ${isDark ? "text-slate-500 group-hover:text-blue-400" : "text-slate-400 group-hover:text-blue-500"} transition-colors`} />
                                            <div className={`absolute left-0 top-6 w-80 p-3 rounded-lg border shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"
                                                }`}>
                                                <p className={`text-xs font-semibold mb-2 ${isDark ? "text-slate-300" : "text-slate-700"}`}>Evaluation Method</p>
                                                <div className="space-y-2 text-xs">
                                                    <div>
                                                        <span className="font-medium text-green-600">✓ VERIFIED:</span>
                                                        <span className={isDark ? "text-slate-400" : "text-slate-600"}> HypoPG simulation with actual cost comparison. Most accurate.</span>
                                                    </div>
                                                    <div>
                                                        <span className="font-medium text-yellow-600">⚠ ESTIMATED:</span>
                                                        <span className={isDark ? "text-slate-400" : "text-slate-600"}> EXPLAIN-based estimation without HypoPG. Reliable but theoretical.</span>
                                                    </div>
                                                    <div>
                                                        <span className="font-medium text-blue-600">◆ ADVISORY:</span>
                                                        <span className={isDark ? "text-slate-400" : "text-slate-600"}> Best-effort suggestions without verification. Review carefully.</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <span className={`text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                            {analysisResult.analysis_type}
                                        </span>
                                    </div>

                                    <p className={`text-sm ${isDark ? "text-slate-300" : "text-slate-600"}`}>
                                        {analysisResult.suggestion?.reasoning}
                                    </p>

                                    {analysisResult.simulation && (
                                        <div className="mt-4 grid grid-cols-3 gap-4">
                                            <div className="text-center">
                                                <div className={`text-xs ${isDark ? "text-slate-500" : "text-slate-400"}`}>Original</div>
                                                <div className={`font-mono ${isDark ? "text-slate-300" : "text-slate-700"}`}>
                                                    {analysisResult.simulation.original_cost?.toFixed(0)}
                                                </div>
                                            </div>
                                            <div className="text-center">
                                                <div className={`text-xs ${isDark ? "text-slate-500" : "text-slate-400"}`}>New</div>
                                                <div className="font-mono text-green-500">
                                                    {analysisResult.simulation.new_cost?.toFixed(0)}
                                                </div>
                                            </div>
                                            <div className="text-center">
                                                <div className={`text-xs ${isDark ? "text-slate-500" : "text-slate-400"}`}>Improvement</div>
                                                <div className="font-bold text-green-500">
                                                    {analysisResult.simulation.improvement_percent}%
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {analysisResult.suggestion?.sql && (
                                        <div className="mt-4">
                                            <div className={`rounded-lg overflow-hidden ${isDark ? "bg-slate-900" : "bg-slate-800"}`}>
                                                <div className="flex items-center justify-between px-3 py-2">
                                                    <span className="text-xs text-slate-500">Suggested SQL</span>
                                                    <button
                                                        onClick={() => copyToClipboard(analysisResult.suggestion.sql, "SQL")}
                                                        className="text-xs text-blue-500 hover:text-blue-400"
                                                    >
                                                        Copy
                                                    </button>
                                                </div>
                                                <pre className="p-3 text-xs text-slate-300 font-mono overflow-x-auto">
                                                    {analysisResult.suggestion.sql}
                                                </pre>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === "plan" && (
                        <div className={`text-center py-12 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                            <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-30" />
                            <p>Execution plan visualization coming soon</p>
                            <p className="text-sm mt-1">Run &quot;Analyze Query&quot; to see optimization suggestions</p>
                        </div>
                    )}

                    {activeTab === "stats" && (
                        <div className={`text-center py-12 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                            <Table2 className="w-12 h-12 mx-auto mb-4 opacity-30" />
                            <p>Table statistics coming soon</p>
                            <p className="text-sm mt-1">Will show row counts, vacuum times, and index usage</p>
                        </div>
                    )}
                </div>
            </div>
        </>
    );
}
