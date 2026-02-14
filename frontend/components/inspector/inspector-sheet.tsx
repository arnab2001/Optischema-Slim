"use client";

import { useAppStore } from "@/store/appStore";
import { X, Copy, ExternalLink, Code, BarChart3, Table2, Zap, Info, Play, ShoppingCart, Check } from "lucide-react";
import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { PlanNode } from "./plan-node";
import { VerificationCard } from "./verification-card";
import { useCartStore } from "@/store/cartStore";

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

// ── Plan Summary Bar ─────────────────────────────────────────────────────────

interface CostBreakdown {
    scan: number;
    join: number;
    sort: number;
    aggregate: number;
    other: number;
}

function walkPlan(node: any, totals: CostBreakdown, bottleneck: { type: string; table: string; cost: number }) {
    const type: string = node["Node Type"] || "";
    const cost = node["Total Cost"] || 0;
    const childrenCost = (node.Plans || []).reduce((s: number, c: any) => s + (c["Total Cost"] || 0), 0);
    // Exclusive cost = this node's cost minus what children contributed
    const exclusive = Math.max(0, cost - childrenCost);

    if (type.includes("Scan") || type.includes("Index")) totals.scan += exclusive;
    else if (type.includes("Join")) totals.join += exclusive;
    else if (type.includes("Sort")) totals.sort += exclusive;
    else if (type.includes("Aggregate") || type.includes("Group")) totals.aggregate += exclusive;
    else totals.other += exclusive;

    if (cost > bottleneck.cost) {
        bottleneck.type = type;
        bottleneck.table = node["Relation Name"] || "";
        bottleneck.cost = cost;
    }

    for (const child of node.Plans || []) {
        walkPlan(child, totals, bottleneck);
    }
}

function PlanSummaryBar({ plan, analysisResult }: { plan: any; analysisResult: any }) {
    const totalCost = plan["Total Cost"] || 1;
    const totals: CostBreakdown = { scan: 0, join: 0, sort: 0, aggregate: 0, other: 0 };
    const bottleneck = { type: "", table: "", cost: 0 };
    walkPlan(plan, totals, bottleneck);

    const pct = (val: number) => totalCost > 0 ? ((val / totalCost) * 100).toFixed(0) : "0";
    const hasSuggestion = analysisResult?.suggestion?.sql;

    return (
        <div className="px-4 py-3 border-b border-slate-800 bg-slate-900/60 space-y-2">
            {/* Cost Breakdown */}
            <div className="flex items-center gap-3 text-[10px] font-mono">
                <span className="text-slate-500 uppercase font-bold tracking-wider">Cost</span>
                <div className="flex-1 h-2 rounded-full overflow-hidden flex bg-slate-800">
                    {totals.scan > 0 && <div className="bg-blue-500 h-full" style={{ width: `${pct(totals.scan)}%` }} title={`Scan: ${pct(totals.scan)}%`} />}
                    {totals.join > 0 && <div className="bg-yellow-500 h-full" style={{ width: `${pct(totals.join)}%` }} title={`Join: ${pct(totals.join)}%`} />}
                    {totals.sort > 0 && <div className="bg-purple-500 h-full" style={{ width: `${pct(totals.sort)}%` }} title={`Sort: ${pct(totals.sort)}%`} />}
                    {totals.aggregate > 0 && <div className="bg-pink-500 h-full" style={{ width: `${pct(totals.aggregate)}%` }} title={`Aggregate: ${pct(totals.aggregate)}%`} />}
                    {totals.other > 0 && <div className="bg-slate-600 h-full" style={{ width: `${pct(totals.other)}%` }} title={`Other: ${pct(totals.other)}%`} />}
                </div>
                <span className="text-slate-400 tabular-nums">{totalCost.toFixed(0)}</span>
            </div>

            {/* Breakdown Labels */}
            <div className="flex items-center gap-4 text-[10px] font-mono text-slate-500">
                {totals.scan > 0 && <span><span className="text-blue-400 font-bold">{pct(totals.scan)}%</span> scan</span>}
                {totals.join > 0 && <span><span className="text-yellow-400 font-bold">{pct(totals.join)}%</span> join</span>}
                {totals.sort > 0 && <span><span className="text-purple-400 font-bold">{pct(totals.sort)}%</span> sort</span>}
                {totals.aggregate > 0 && <span><span className="text-pink-400 font-bold">{pct(totals.aggregate)}%</span> agg</span>}
            </div>

            {/* Bottleneck Highlight */}
            {bottleneck.type && (
                <div className="flex items-center justify-between">
                    <div className="text-[10px] text-slate-400">
                        Top bottleneck: <span className="text-red-400 font-bold">{bottleneck.type}</span>
                        {bottleneck.table && <span className="text-slate-500"> on {bottleneck.table}</span>}
                    </div>
                    {hasSuggestion && (
                        <InspectorCartButton analysisResult={analysisResult} query={null} />
                    )}
                </div>
            )}
        </div>
    );
}

function InspectorCartButton({ analysisResult, query }: { analysisResult: any; query: QueryMetric | null }) {
    const { addItem } = useCartStore();
    const sql = analysisResult?.suggestion?.sql;
    const inCart = useCartStore((s) => sql ? s.isInCart(sql) : false);

    if (!sql) return null;

    const category = analysisResult?.analysis_type || analysisResult?.suggestion?.category || "INDEX";

    return (
        <button
            onClick={() => {
                if (!inCart && sql) {
                    const wi = analysisResult?.workload_impact;
                    const impactNote = wi && wi.tested_queries > 0
                        ? ` | Workload: ${wi.improved} improved, ${wi.regressed} regressed, ${wi.neutral} neutral`
                        : '';
                    addItem({
                        id: crypto.randomUUID(),
                        type: category === "INDEX" ? "index" : category === "REWRITE" ? "rewrite" : "drop",
                        sql,
                        description: `${analysisResult?.suggestion?.reasoning?.slice(0, 100) || "Query optimization"}${impactNote}`,
                        table: "",
                        estimatedImprovement: analysisResult?.simulation?.improvement_percent,
                        source: "analysis",
                    });
                }
            }}
            className={`text-xs flex items-center gap-1 ${
                inCart ? "text-blue-400 cursor-default" : "text-green-500 hover:text-green-400"
            }`}
        >
            {inCart ? <Check className="w-3 h-3" /> : <ShoppingCart className="w-3 h-3" />}
            {inCart ? "In Cart" : "Add to Cart"}
        </button>
    );
}

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
    const [verifying, setVerifying] = useState(false);
    const [verificationResult, setVerificationResult] = useState<any>(null);

    const apiUrl = import.meta.env.VITE_API_URL || "";

    // Auto-load cached analysis when query changes (hits backend cache, no LLM cost)
    useEffect(() => {
        setAnalysisError(null);
        setVerificationResult(null);
        setActiveTab("sql");

        if (query?.query) {
            // Try to load cached result only (cache_only=true means no LLM call, no cost)
            setAnalysisResult(null);
            (async () => {
                try {
                    const res = await fetch(`${apiUrl}/api/analysis/analyze`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ query: query.query, cache_only: true }),
                    });
                    if (res.ok) {
                        const data = await res.json();
                        if (data._cached && !data._no_result) {
                            setAnalysisResult(data);
                        }
                    }
                } catch {
                    // Silently fail — user can click Analyze manually
                }
            })();
        } else {
            setAnalysisResult(null);
        }
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

    const runAnalysis = async (refresh = false) => {
        if (!query) return;

        setAnalyzing(true);
        setAnalysisError(null);
        if (refresh) setAnalysisResult(null);

        try {
            const res = await fetch(`${apiUrl}/api/analysis/analyze`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: query.query, refresh }),
            });

            if (res.ok) {
                const data = await res.json();
                setAnalysisResult(data);
                toast.success(data._cached ? "Loaded from cache" : "Analysis complete");
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

    const verifyImpact = async () => {
        if (!query || !analysisResult?.suggestion?.sql) return;

        setVerifying(true);
        setVerificationResult(null);

        try {
            const res = await fetch(`${apiUrl}/api/analysis/verify`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query: query.query,
                    sql: analysisResult.suggestion.sql
                }),
            });

            if (res.ok) {
                const data = await res.json();
                setVerificationResult(data);
                if (data.error) {
                    toast.error("Simulation failed");
                } else {
                    toast.success("Simulation complete");
                }
            } else {
                toast.error("Verification request failed");
            }
        } catch (e) {
            toast.error("Network error during verification");
        } finally {
            setVerifying(false);
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
                <div className={`h-16 flex items-center justify-between px-6 border-b ${isDark ? "border-slate-800" : "border-slate-200"
                    }`}>
                    <div className="flex items-center gap-4">
                        <div className="flex flex-col">
                            <span className={`text-[10px] uppercase font-bold tracking-[0.2em] ${isDark ? "text-slate-500" : "text-slate-400"}`}>Query Inspector</span>
                            <span className={`font-mono text-xl font-black ${isDark ? "text-white" : "text-slate-900"}`}>
                                QID:{query.queryid.substring(0, 12).toUpperCase()}
                            </span>
                        </div>
                        <button
                            onClick={() => copyToClipboard(query.queryid, "ID")}
                            className={`p-1.5 rounded hover:bg-opacity-10 transition-colors ${isDark ? "text-slate-400 hover:bg-white" : "text-slate-500 hover:bg-black"
                                }`}
                            title="Copy Query ID"
                        >
                            <Copy className="w-3.5 h-3.5" />
                        </button>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => copyToClipboard(window.location.href, "Link")}
                            className={`p-2 rounded-lg hover:bg-opacity-10 transition-colors ${isDark ? "text-slate-400 hover:bg-white" : "text-slate-500 hover:bg-black"
                                }`}
                            title="Copy link"
                        >
                            <ExternalLink className="w-5 h-5" />
                        </button>
                        <button
                            onClick={onClose}
                            className={`p-2 rounded-lg ${isDark ? "text-slate-400 hover:bg-slate-800" : "text-slate-500 hover:bg-slate-100"
                                }`}
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
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
                                onClick={() => runAnalysis()}
                                disabled={analyzing}
                                className={`w-full py-3 rounded-lg font-medium flex items-center justify-center gap-2 disabled:opacity-50 ${analysisError
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
                                        {analysisResult._cached && (
                                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${
                                                isDark ? "bg-slate-700 text-slate-400" : "bg-slate-100 text-slate-500"
                                            }`}>
                                                cached {analysisResult._cache_age_seconds != null
                                                    ? analysisResult._cache_age_seconds < 60
                                                        ? `${analysisResult._cache_age_seconds}s ago`
                                                        : `${Math.floor(analysisResult._cache_age_seconds / 60)}m ago`
                                                    : ""}
                                            </span>
                                        )}
                                        {analysisResult._cached && (
                                            <button
                                                onClick={() => runAnalysis(true)}
                                                disabled={analyzing}
                                                className={`text-[10px] font-medium px-2 py-0.5 rounded-full transition-colors ${
                                                    isDark
                                                        ? "text-blue-400 hover:bg-blue-900/30"
                                                        : "text-blue-600 hover:bg-blue-50"
                                                }`}
                                            >
                                                Re-analyze
                                            </button>
                                        )}
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

                                    {/* Confidence Score & Factors */}
                                    {analysisResult.confidence_score != null && (
                                        <div className="mt-3 space-y-2">
                                            <div className="flex items-center gap-2">
                                                <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                                                    <div
                                                        className={`h-full rounded-full ${
                                                            analysisResult.confidence_score >= 80 ? 'bg-green-500' :
                                                            analysisResult.confidence_score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                                                        }`}
                                                        style={{ width: `${analysisResult.confidence_score}%` }}
                                                    />
                                                </div>
                                                <span className={`text-[10px] font-bold ${
                                                    analysisResult.confidence_score >= 80 ? 'text-green-400' :
                                                    analysisResult.confidence_score >= 50 ? 'text-yellow-400' : 'text-red-400'
                                                }`}>
                                                    {analysisResult.confidence_score >= 80 ? 'High' :
                                                     analysisResult.confidence_score >= 50 ? 'Medium' : 'Low'} Confidence ({analysisResult.confidence_score}%)
                                                </span>
                                            </div>

                                            {analysisResult.confidence_factors && analysisResult.confidence_factors.length > 0 && (
                                                <details className="group">
                                                    <summary className={`text-xs cursor-pointer font-medium ${isDark ? "text-blue-400 hover:text-blue-300" : "text-blue-600 hover:text-blue-500"}`}>
                                                        Why this recommendation?
                                                    </summary>
                                                    <ul className={`mt-1.5 space-y-1 text-xs ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                                        {analysisResult.confidence_factors.map((factor: string, i: number) => (
                                                            <li key={i} className="flex items-start gap-1.5">
                                                                <span className="text-green-500 mt-0.5 flex-shrink-0">&#x2713;</span>
                                                                {factor}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </details>
                                            )}
                                        </div>
                                    )}

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
                                                    <div className="flex items-center gap-2">
                                                        <InspectorCartButton analysisResult={analysisResult} query={query} />
                                                        <button
                                                            onClick={() => copyToClipboard(analysisResult.suggestion.sql, "SQL")}
                                                            className="text-xs text-blue-500 hover:text-blue-400"
                                                        >
                                                            Copy
                                                        </button>
                                                    </div>
                                                </div>
                                                <div className="text-xs">
                                                    <SyntaxHighlighter
                                                        language="sql"
                                                        style={vscDarkPlus}
                                                        customStyle={{ margin: 0, padding: '12px', background: 'transparent' }}
                                                        showLineNumbers={false}
                                                    >
                                                        {analysisResult.suggestion.sql}
                                                    </SyntaxHighlighter>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Verification Result Display */}
                                    {verificationResult && (
                                        <VerificationCard result={verificationResult} />
                                    )}

                                    {/* Evaluation Action Bar */}
                                    <div className={`flex items-center justify-between mt-4 pt-4 border-t ${isDark ? 'border-slate-700' : 'border-slate-200'}`}>
                                        <div className={`text-[10px] uppercase font-bold tracking-widest ${isDark ? 'text-slate-600' : 'text-slate-400'}`}>
                                            Sandbox Engine: <span className="text-blue-500">HypoPG</span>
                                        </div>
                                        {/* Hide if already verified automatically */}
                                        {!(analysisResult.verification_status === "verified" && !verificationResult) && (
                                            <button
                                                onClick={verifyImpact}
                                                disabled={verifying}
                                                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-bold uppercase tracking-wider text-white transition-all transform active:scale-95 disabled:opacity-50 ${verifying ? "bg-slate-600" : "bg-blue-600 hover:bg-blue-500 shadow-lg shadow-blue-500/20"
                                                    }`}
                                            >
                                                {verifying ? (
                                                    <>
                                                        <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                                        Verifying...
                                                    </>
                                                ) : (
                                                    <>
                                                        <Play className="w-3 h-3 fill-current" />
                                                        Verify Impact
                                                    </>
                                                )}
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === "plan" && (
                        <div className="p-0 h-full">
                            {analysisResult?.original_plan ? (
                                <div className={`h-full overflow-auto bg-black border-t ${isDark ? "border-slate-800" : "border-slate-200"}`}>
                                    {/* Plan Summary Bar */}
                                    <PlanSummaryBar plan={analysisResult.original_plan} analysisResult={analysisResult} />

                                    <div className="p-4">
                                        <div className="flex items-center justify-between mb-4">
                                            <h3 className="text-[10px] uppercase font-bold tracking-widest text-slate-500">Execution Plan</h3>
                                            <div className="flex items-center gap-4 text-[10px] font-mono text-slate-500">
                                                <div className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-green-500" /> 0-10%</div>
                                                <div className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-yellow-500" /> 10-30%</div>
                                                <div className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-orange-500" /> 30-60%</div>
                                                <div className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-red-500" /> 60%+</div>
                                            </div>
                                        </div>
                                        <PlanNode node={analysisResult.original_plan} />
                                    </div>
                                </div>
                            ) : (
                                <div className={`text-center py-12 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                    <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-30" />
                                    {analyzing ? (
                                        <p>Analyzing query plan...</p>
                                    ) : (
                                        <>
                                            <p>No execution plan available</p>
                                            <p className="text-sm mt-1">Run "Analyze Query" to generate a plan</p>
                                        </>
                                    )}
                                </div>
                            )}
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
