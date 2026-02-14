"use client";

import { useState, useEffect } from "react";
import { useAppStore } from "@/store/appStore";
import {
    Database,
    RefreshCw,
    AlertTriangle,
    Info,
    CheckCircle2,
    ChevronDown,
    ChevronUp,
    Package,
    FileWarning,
    Sparkles,
    Clock,
    Zap,
    Shield,
    TrendingUp
} from "lucide-react";
import { toast } from "sonner";

interface SchemaIssue {
    severity: "P0" | "P1" | "P2";
    type: string;
    table: string;
    message: string;
    impact: string;
    recommendation: string;
    metadata: Record<string, any>;
}

interface SchemaHealthResult {
    success: boolean;
    summary: {
        total_tables: number;
        tables_with_issues: number;
        p0_count: number;
        p1_count: number;
        p2_count: number;
    };
    issues: SchemaIssue[];
    error?: string;
    _cached?: boolean;
    _cache_age_seconds?: number;
}

interface AIPriority {
    priority: number;
    title: string;
    description: string;
    impact: "high" | "medium" | "low";
    effort: "quick" | "moderate" | "significant";
}

interface AISummaryData {
    overall_grade: string;
    one_liner: string;
    priorities: AIPriority[];
    quick_wins: string[];
    risks: string[];
}

interface AISummaryResult {
    success: boolean;
    summary?: AISummaryData;
    error?: string;
    _cached?: boolean;
    _cache_age_seconds?: number;
}

export function SchemaHealth() {
    const { theme } = useAppStore();
    const isDark = theme === "dark";

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<SchemaHealthResult | null>(null);
    const [expandedIssues, setExpandedIssues] = useState<Set<number>>(new Set());

    const [aiLoading, setAiLoading] = useState(false);
    const [aiSummary, setAiSummary] = useState<AISummaryResult | null>(null);
    const [aiExpanded, setAiExpanded] = useState(true);

    const apiUrl = import.meta.env.VITE_API_URL || "";

    // Auto-load cached schema results on mount (AI summary loaded only after schema data exists)
    useEffect(() => {
        fetchCached();
    }, []);

    const fetchCached = async () => {
        try {
            const res = await fetch(`${apiUrl}/api/health/schema`);
            const data = await res.json();
            if (data.success) {
                setResult(data);
                // Only try loading cached AI summary if schema data exists
                fetchAiSummary(false);
            }
        } catch {
            // Silently fail — user can manually scan
        }
    };

    const runAnalysis = async (refresh = true) => {
        setLoading(true);
        try {
            const res = await fetch(`${apiUrl}/api/health/schema?refresh=${refresh}`);
            const data = await res.json();
            if (data.success) {
                setResult(data);
                toast.success("Schema analysis complete");
            } else {
                toast.error(data.error || "Schema analysis failed");
            }
        } catch (e) {
            toast.error("Failed to analyze schema");
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const fetchAiSummary = async (refresh = false) => {
        setAiLoading(true);
        try {
            const res = await fetch(`${apiUrl}/api/health/schema/ai-summary?refresh=${refresh}`);
            const data = await res.json();
            if (data.success && data.summary && data.summary.overall_grade) {
                // Normalize LLM output — ensure arrays always exist
                data.summary.priorities = Array.isArray(data.summary.priorities) ? data.summary.priorities : [];
                data.summary.quick_wins = Array.isArray(data.summary.quick_wins) ? data.summary.quick_wins : [];
                data.summary.risks = Array.isArray(data.summary.risks) ? data.summary.risks : [];
                data.summary.one_liner = data.summary.one_liner || "";
                setAiSummary(data);
            } else if (data.success && data.summary && !data.summary.overall_grade) {
                // Stale/malformed cache entry — ignore it, user can regenerate
                console.warn("AI summary missing expected structure, ignoring cached result");
            }
        } catch {
            // Silently fail
        } finally {
            setAiLoading(false);
        }
    };

    const toggleIssue = (index: number) => {
        const newExpanded = new Set(expandedIssues);
        if (newExpanded.has(index)) {
            newExpanded.delete(index);
        } else {
            newExpanded.add(index);
        }
        setExpandedIssues(newExpanded);
    };

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case "P0": return "text-red-500 bg-red-500/10 border-red-500/20";
            case "P1": return "text-orange-500 bg-orange-500/10 border-orange-500/20";
            case "P2": return "text-yellow-500 bg-yellow-500/10 border-yellow-500/20";
            default: return "text-slate-500 bg-slate-500/10 border-slate-500/20";
        }
    };

    const getSeverityIcon = (severity: string) => {
        switch (severity) {
            case "P0": return <AlertTriangle className="w-4 h-4" />;
            case "P1": return <FileWarning className="w-4 h-4" />;
            case "P2": return <Info className="w-4 h-4" />;
            default: return <Info className="w-4 h-4" />;
        }
    };

    const getTypeLabel = (type: string) => {
        return type.split("_").map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
    };

    const getGradeColor = (grade: string) => {
        switch (grade) {
            case "A": return "text-green-500 bg-green-500/10 border-green-500/30";
            case "B": return "text-blue-500 bg-blue-500/10 border-blue-500/30";
            case "C": return "text-yellow-500 bg-yellow-500/10 border-yellow-500/30";
            case "D": return "text-orange-500 bg-orange-500/10 border-orange-500/30";
            case "F": return "text-red-500 bg-red-500/10 border-red-500/30";
            default: return "text-slate-500 bg-slate-500/10 border-slate-500/30";
        }
    };

    const getImpactColor = (impact: string) => {
        switch (impact) {
            case "high": return "text-red-400 bg-red-500/10";
            case "medium": return "text-yellow-400 bg-yellow-500/10";
            case "low": return "text-green-400 bg-green-500/10";
            default: return "text-slate-400 bg-slate-500/10";
        }
    };

    const getEffortLabel = (effort: string) => {
        switch (effort) {
            case "quick": return { label: "Quick", color: "text-green-400" };
            case "moderate": return { label: "Moderate", color: "text-yellow-400" };
            case "significant": return { label: "Significant", color: "text-orange-400" };
            default: return { label: effort, color: "text-slate-400" };
        }
    };

    const formatCacheAge = (seconds: number) => {
        if (seconds < 60) return `${seconds}s ago`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        return `${Math.floor(seconds / 3600)}h ago`;
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className={`text-xl font-bold ${isDark ? "text-white" : "text-slate-900"}`}>
                        Schema Health
                    </h2>
                    <p className={`text-sm flex items-center gap-2 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                        Detect schema design issues that impact performance
                        {result?._cached && result._cache_age_seconds != null && (
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${
                                isDark ? "bg-slate-700 text-slate-400" : "bg-slate-100 text-slate-500"
                            }`}>
                                <Clock className="w-2.5 h-2.5" />
                                cached {formatCacheAge(result._cache_age_seconds)}
                            </span>
                        )}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    {result && (
                        <button
                            onClick={() => runAnalysis(true)}
                            disabled={loading}
                            className={`px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-1.5 border ${
                                isDark
                                    ? "border-slate-600 text-slate-300 hover:bg-slate-700"
                                    : "border-slate-200 text-slate-600 hover:bg-slate-50"
                            }`}
                        >
                            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                            Fresh Scan
                        </button>
                    )}
                    {!result && (
                        <button
                            onClick={() => runAnalysis(false)}
                            disabled={loading}
                            className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 ${
                                loading
                                    ? "bg-blue-500/50 text-white cursor-not-allowed"
                                    : "bg-blue-600 hover:bg-blue-700 text-white"
                            }`}
                        >
                            {loading ? (
                                <><RefreshCw className="w-4 h-4 animate-spin" /> Analyzing...</>
                            ) : (
                                <><Database className="w-4 h-4" /> Run Analysis</>
                            )}
                        </button>
                    )}
                </div>
            </div>

            {/* ── AI Summary Card ─────────────────────────────────────────── */}
            {aiSummary?.success && aiSummary.summary && (
                <div className={`rounded-xl border overflow-hidden ${
                    isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"
                }`}>
                    {/* AI Summary Header */}
                    <div
                        className="p-4 flex items-center justify-between cursor-pointer"
                        onClick={() => setAiExpanded(!aiExpanded)}
                    >
                        <div className="flex items-center gap-3">
                            <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-xl font-black border-2 ${getGradeColor(aiSummary.summary.overall_grade)}`}>
                                {aiSummary.summary.overall_grade}
                            </div>
                            <div>
                                <div className="flex items-center gap-2">
                                    <Sparkles className="w-4 h-4 text-purple-500" />
                                    <span className={`text-sm font-bold ${isDark ? "text-white" : "text-slate-900"}`}>
                                        AI Assessment
                                    </span>
                                    {aiSummary._cached && aiSummary._cache_age_seconds != null && (
                                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${
                                            isDark ? "bg-slate-700 text-slate-400" : "bg-slate-100 text-slate-500"
                                        }`}>
                                            <Clock className="w-2.5 h-2.5" />
                                            {formatCacheAge(aiSummary._cache_age_seconds)}
                                        </span>
                                    )}
                                </div>
                                <p className={`text-xs mt-0.5 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                    {aiSummary.summary.one_liner}
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={(e) => { e.stopPropagation(); fetchAiSummary(true); }}
                                disabled={aiLoading}
                                className={`p-1.5 rounded-md ${
                                    isDark ? "hover:bg-slate-700 text-slate-400" : "hover:bg-slate-100 text-slate-500"
                                }`}
                                title="Refresh AI summary"
                            >
                                <RefreshCw className={`w-3.5 h-3.5 ${aiLoading ? "animate-spin" : ""}`} />
                            </button>
                            {aiExpanded ? (
                                <ChevronUp className="w-4 h-4 text-slate-400" />
                            ) : (
                                <ChevronDown className="w-4 h-4 text-slate-400" />
                            )}
                        </div>
                    </div>

                    {/* AI Summary Body */}
                    {aiExpanded && (
                        <div className={`px-4 pb-4 space-y-4 border-t ${isDark ? "border-slate-700" : "border-slate-200"}`}>
                            {/* Priorities */}
                            {aiSummary.summary.priorities.length > 0 && (
                                <div className="pt-4">
                                    <h4 className={`text-xs font-bold uppercase tracking-wider mb-3 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                        Top Priorities
                                    </h4>
                                    <div className="space-y-2">
                                        {aiSummary.summary.priorities.map((p, i) => {
                                            const effort = getEffortLabel(p.effort);
                                            return (
                                                <div key={i} className={`p-3 rounded-lg ${isDark ? "bg-slate-900/50" : "bg-slate-50"}`}>
                                                    <div className="flex items-start gap-3">
                                                        <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black flex-shrink-0 ${
                                                            i === 0 ? "bg-red-500/20 text-red-400" :
                                                            i === 1 ? "bg-orange-500/20 text-orange-400" :
                                                            "bg-slate-500/20 text-slate-400"
                                                        }`}>
                                                            {p.priority}
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <div className="flex items-center gap-2 flex-wrap">
                                                                <span className={`text-sm font-medium ${isDark ? "text-white" : "text-slate-900"}`}>
                                                                    {p.title}
                                                                </span>
                                                                <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${getImpactColor(p.impact)}`}>
                                                                    {p.impact}
                                                                </span>
                                                                <span className={`text-[9px] font-medium ${effort.color}`}>
                                                                    {effort.label}
                                                                </span>
                                                            </div>
                                                            <p className={`text-xs mt-1 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                                                {p.description}
                                                            </p>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {/* Quick Wins & Risks side by side */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {aiSummary.summary.quick_wins.length > 0 && (
                                    <div className={`p-3 rounded-lg ${isDark ? "bg-green-900/10" : "bg-green-50"}`}>
                                        <div className="flex items-center gap-1.5 mb-2">
                                            <Zap className="w-3.5 h-3.5 text-green-500" />
                                            <span className={`text-xs font-bold ${isDark ? "text-green-400" : "text-green-700"}`}>
                                                Quick Wins
                                            </span>
                                        </div>
                                        <ul className="space-y-1.5">
                                            {aiSummary.summary.quick_wins.map((win, i) => (
                                                <li key={i} className={`text-xs flex items-start gap-1.5 ${isDark ? "text-green-300/80" : "text-green-700/80"}`}>
                                                    <TrendingUp className="w-3 h-3 flex-shrink-0 mt-0.5" />
                                                    {win}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {aiSummary.summary.risks.length > 0 && (
                                    <div className={`p-3 rounded-lg ${isDark ? "bg-red-900/10" : "bg-red-50"}`}>
                                        <div className="flex items-center gap-1.5 mb-2">
                                            <Shield className="w-3.5 h-3.5 text-red-500" />
                                            <span className={`text-xs font-bold ${isDark ? "text-red-400" : "text-red-700"}`}>
                                                Risks to Watch
                                            </span>
                                        </div>
                                        <ul className="space-y-1.5">
                                            {aiSummary.summary.risks.map((risk, i) => (
                                                <li key={i} className={`text-xs flex items-start gap-1.5 ${isDark ? "text-red-300/80" : "text-red-700/80"}`}>
                                                    <AlertTriangle className="w-3 h-3 flex-shrink-0 mt-0.5" />
                                                    {risk}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* AI Summary Loading State */}
            {aiLoading && !aiSummary && (
                <div className={`p-6 rounded-xl border flex items-center justify-center gap-3 ${
                    isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"
                }`}>
                    <RefreshCw className="w-4 h-4 animate-spin text-purple-500" />
                    <span className={`text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                        Generating AI assessment...
                    </span>
                </div>
            )}

            {/* Generate AI Summary Button (when schema data exists but no AI summary) */}
            {result && !aiSummary && !aiLoading && (
                <button
                    onClick={() => fetchAiSummary(true)}
                    className={`w-full py-3 rounded-xl border text-sm font-medium flex items-center justify-center gap-2 transition-all ${
                        isDark
                            ? "border-purple-800 text-purple-400 hover:bg-purple-900/20 bg-slate-800"
                            : "border-purple-200 text-purple-600 hover:bg-purple-50 bg-white"
                    }`}
                >
                    <Sparkles className="w-4 h-4" />
                    Generate AI Assessment
                </button>
            )}

            {/* Summary Cards */}
            {result && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className={`p-4 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                        <div className="flex items-center gap-2 mb-2">
                            <Package className="w-4 h-4 text-blue-500" />
                            <span className={`text-xs font-bold uppercase tracking-wider ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                Tables
                            </span>
                        </div>
                        <div className={`text-2xl font-bold ${isDark ? "text-white" : "text-slate-800"}`}>
                            {result.summary.total_tables}
                        </div>
                        <div className={`text-xs mt-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                            {result.summary.tables_with_issues} with issues
                        </div>
                    </div>

                    <div className={`p-4 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                        <div className="flex items-center gap-2 mb-2">
                            <AlertTriangle className="w-4 h-4 text-red-500" />
                            <span className={`text-xs font-bold uppercase tracking-wider ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                Critical (P0)
                            </span>
                        </div>
                        <div className="text-2xl font-bold text-red-500">{result.summary.p0_count}</div>
                        <div className={`text-xs mt-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                            Requires immediate attention
                        </div>
                    </div>

                    <div className={`p-4 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                        <div className="flex items-center gap-2 mb-2">
                            <FileWarning className="w-4 h-4 text-orange-500" />
                            <span className={`text-xs font-bold uppercase tracking-wider ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                High (P1)
                            </span>
                        </div>
                        <div className="text-2xl font-bold text-orange-500">{result.summary.p1_count}</div>
                        <div className={`text-xs mt-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                            Optimization opportunities
                        </div>
                    </div>

                    <div className={`p-4 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                        <div className="flex items-center gap-2 mb-2">
                            <Info className="w-4 h-4 text-yellow-500" />
                            <span className={`text-xs font-bold uppercase tracking-wider ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                Medium (P2)
                            </span>
                        </div>
                        <div className="text-2xl font-bold text-yellow-500">{result.summary.p2_count}</div>
                        <div className={`text-xs mt-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                            Consider reviewing
                        </div>
                    </div>
                </div>
            )}

            {/* Issues List */}
            {result && result.issues.length > 0 && (
                <div className={`rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                    <div className={`p-4 border-b ${isDark ? "border-slate-700" : "border-slate-200"}`}>
                        <h3 className={`text-sm font-bold ${isDark ? "text-white" : "text-slate-900"}`}>
                            Detected Issues ({result.issues.length})
                        </h3>
                    </div>
                    <div className={`divide-y ${isDark ? "divide-slate-700" : "divide-slate-200"}`}>
                        {result.issues.map((issue, index) => {
                            const isExpanded = expandedIssues.has(index);
                            return (
                                <div key={index} className="p-4">
                                    {/* Issue Header */}
                                    <div
                                        className="flex items-start gap-3 cursor-pointer"
                                        onClick={() => toggleIssue(index)}
                                    >
                                        <div className={`px-2 py-1 rounded text-xs font-bold flex items-center gap-1 ${getSeverityColor(issue.severity)}`}>
                                            {getSeverityIcon(issue.severity)}
                                            {issue.severity}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-start justify-between gap-2">
                                                <div className="flex-1">
                                                    <h4 className={`text-sm font-medium ${isDark ? "text-white" : "text-slate-900"}`}>
                                                        {issue.message}
                                                    </h4>
                                                    <p className={`text-xs mt-1 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                                        {getTypeLabel(issue.type)} &middot; {issue.table}
                                                    </p>
                                                </div>
                                                {isExpanded ? (
                                                    <ChevronUp className="w-4 h-4 text-slate-400 flex-shrink-0" />
                                                ) : (
                                                    <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Issue Details (Expanded) */}
                                    {isExpanded && (
                                        <div className="mt-4 ml-8 space-y-3">
                                            <div className={`p-3 rounded-lg ${isDark ? "bg-slate-900/50" : "bg-slate-50"}`}>
                                                <p className={`text-xs font-bold uppercase tracking-wider mb-1 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                                    Impact
                                                </p>
                                                <p className={`text-sm ${isDark ? "text-slate-300" : "text-slate-700"}`}>
                                                    {issue.impact}
                                                </p>
                                            </div>

                                            <div className={`p-3 rounded-lg ${isDark ? "bg-blue-900/20" : "bg-blue-50"}`}>
                                                <p className={`text-xs font-bold uppercase tracking-wider mb-1 ${isDark ? "text-blue-400" : "text-blue-700"}`}>
                                                    Recommendation
                                                </p>
                                                <p className={`text-sm ${isDark ? "text-blue-300" : "text-blue-800"}`}>
                                                    {issue.recommendation}
                                                </p>
                                            </div>

                                            {Object.keys(issue.metadata).length > 0 && (
                                                <details className={`text-xs ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                                    <summary className="cursor-pointer hover:text-blue-500">
                                                        Technical Details
                                                    </summary>
                                                    <pre className={`mt-2 p-2 rounded text-xs overflow-x-auto ${isDark ? "bg-slate-900" : "bg-slate-100"}`}>
                                                        {JSON.stringify(issue.metadata, null, 2)}
                                                    </pre>
                                                </details>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* No Issues State */}
            {result && result.issues.length === 0 && (
                <div className={`p-12 text-center rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                    <CheckCircle2 className={`w-12 h-12 mx-auto mb-4 ${isDark ? "text-green-400" : "text-green-500"}`} />
                    <h3 className={`text-lg font-medium mb-1 ${isDark ? "text-slate-200" : "text-slate-800"}`}>
                        Schema Looks Good!
                    </h3>
                    <p className={isDark ? "text-slate-400" : "text-slate-500"}>
                        No critical schema design issues detected across {result.summary.total_tables} tables.
                    </p>
                </div>
            )}

            {/* Empty State */}
            {!result && !loading && (
                <div className={`p-12 text-center rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                    <Database className={`w-12 h-12 mx-auto mb-4 ${isDark ? "text-slate-600" : "text-slate-300"}`} />
                    <h3 className={`text-lg font-medium mb-1 ${isDark ? "text-slate-200" : "text-slate-800"}`}>
                        Ready to Analyze
                    </h3>
                    <p className={`mb-4 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                        Click "Run Analysis" to scan your database schema for design issues.
                    </p>
                </div>
            )}
        </div>
    );
}
