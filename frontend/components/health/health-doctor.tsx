"use client";

import { useState, useEffect } from "react";
import { useAppStore } from "@/store/appStore";
import { useRouter } from "next/navigation";
import {
    Activity,
    RefreshCw,
    Database,
    Clock,
    Check,
    AlertTriangle,
    CheckCircle2,
    FileX,
    Settings,
    ChevronDown,
    ChevronUp,
    ShieldCheck,
    Zap,
    X,
    Clipboard,
    History,
    Info,
    ArrowRight
} from "lucide-react";
import { toast } from "sonner";
import { HealthScoreGauge } from "./health-score-gauge";
import { IssueCard } from "./issue-card";

interface Issue {
    type: "QUERY" | "CONFIG" | "SCHEMA" | "SYSTEM";
    severity: "CRITICAL" | "WARNING" | "INFO";
    title: string;
    description: string;
    action_payload: string;
}

interface TableBloatIssue {
    schema: string;
    table: string;
    dead_ratio: number;
    live_tuples: number;
    dead_tuples: number;
    last_autovacuum: string | null;
    vacuum_overdue: boolean;
    severity: "low" | "medium" | "high";
    recommendation: string;
}

interface IndexIssue {
    schema: string;
    table: string;
    index: string;
    scans: number;
    tuples_read: number;
    tuples_fetched: number;
    size: string;
    size_bytes: number;
    severity: string;
    recommendation: string;
}

interface ConfigIssue {
    setting: string;
    current_value: string;
    severity: "low" | "medium" | "high";
    issue: string;
    recommendation: string;
}

interface ScanResult {
    id?: number;
    health_score: number;
    issues: Issue[];
    scan_timestamp: string;
    score_breakdown?: string[];
    table_bloat: {
        checked: boolean;
        issues: TableBloatIssue[];
        total_tables_checked: number;
    };
    index_bloat: {
        checked: boolean;
        unused_indexes: IndexIssue[];
        total_unused: number;
    };
    config_issues: {
        checked: boolean;
        issues: ConfigIssue[];
        total_settings_checked: number;
    };
    summary: {
        total_bloated_tables: number;
        total_unused_indexes: number;
        total_config_issues: number;
    };
    error?: string;
}

export function HealthDoctor() {
    const { theme, setSelectedQueryId } = useAppStore();
    const router = useRouter();
    const isDark = theme === "dark";

    const [scanLimit, setScanLimit] = useState(50);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<ScanResult | null>(null);
    const [expandedSection, setExpandedSection] = useState<string | null>(null);
    const [showSqlModal, setShowSqlModal] = useState<string | null>(null);
    const [showMethodology, setShowMethodology] = useState(false);
    const [copied, setCopied] = useState(false);

    // History State
    const [showHistory, setShowHistory] = useState(false);
    const [history, setHistory] = useState<ScanResult[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(false);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

    const fetchLatest = async () => {
        try {
            const res = await fetch(`${apiUrl}/api/health/latest`);
            if (res.ok) {
                const data = await res.json();
                setResult(data);
            }
        } catch (e) {
            console.error("Failed to fetch latest health result", e);
        }
    };

    const fetchHistory = async () => {
        setLoadingHistory(true);
        try {
            const res = await fetch(`${apiUrl}/api/health/history?limit=10`);
            if (res.ok) {
                const data = await res.json();
                setHistory(data);
            }
        } catch (e) {
            toast.error("Failed to fetch history");
        } finally {
            setLoadingHistory(false);
        }
    };

    useEffect(() => {
        fetchLatest();
    }, []);

    useEffect(() => {
        if (showHistory) {
            fetchHistory();
        }
    }, [showHistory]);

    const runScan = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${apiUrl}/api/health/scan`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ limit: scanLimit })
            });
            if (res.ok) {
                const data = await res.json();
                setResult(data);
                toast.success(`Health scan complete (${scanLimit} items analyzed)`);
            } else {
                toast.error("Failed to run health scan");
            }
        } catch (e) {
            toast.error("Network error running health scan");
        } finally {
            setLoading(false);
        }
    };

    const handleIssueAction = (issue: Issue) => {
        if (issue.type === "QUERY") {
            setSelectedQueryId(issue.action_payload);
            router.push("/dashboard"); // Navigate to Monitor view
        } else if (issue.type === "SCHEMA" || issue.type === "CONFIG") {
            setShowSqlModal(issue.action_payload);
        }
    };

    const copyToClipboard = () => {
        if (showSqlModal) {
            navigator.clipboard.writeText(showSqlModal);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
            toast.success("SQL copied to clipboard");
        }
    };

    const getHealthBgColor = (score: number) => {
        if (score >= 80) return isDark ? "bg-green-500/5 border-green-500/20" : "bg-green-50 border-green-200/50";
        if (score >= 50) return isDark ? "bg-yellow-500/5 border-yellow-500/20" : "bg-yellow-50 border-yellow-200/50";
        return isDark ? "bg-red-500/5 border-red-500/20" : "bg-red-50 border-red-200/50";
    };

    const getSeverityColor = (severity: string) => {
        switch (severity.toLowerCase()) {
            case "high": case "critical":
                return "text-red-500 bg-red-500/10 border-red-500/20";
            case "medium": case "warning":
                return "text-yellow-600 bg-yellow-500/10 border-yellow-500/20";
            default:
                return "text-blue-500 bg-blue-500/10 border-blue-500/20";
        }
    };

    const generateConfigSql = (setting: string, recommendation: string) => {
        let value = "/* appropriate_value */";
        if (setting === "work_mem") value = "'16MB'";
        else if (setting === "shared_buffers") value = "'1GB'";
        else if (setting === "autovacuum_vacuum_scale_factor") value = "0.05";

        return `-- Prescription: ${recommendation}\nALTER SYSTEM SET ${setting} = ${value};\nSELECT pg_reload_conf();`;
    };

    const cardClass = `rounded-xl border shadow-sm ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`;

    return (
        <div className="space-y-6">
            {/* Main Header & Gauge */}
            <div className={cardClass}>
                <div className={`p-4 border-b flex items-center justify-between ${isDark ? "border-slate-700" : "border-slate-200"}`}>
                    <div className="flex flex-col">
                        <h2 className={`text-lg font-semibold flex items-center gap-2 ${isDark ? "text-white" : "text-slate-800"}`}>
                            <Activity className="w-5 h-5 text-blue-500" />
                            Health Doctor
                        </h2>
                        {result?.scan_timestamp && (
                            <div className={`text-xs flex items-center gap-1.5 mt-0.5 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                <Clock className="w-3.5 h-3.5" />
                                <span>Last scan: {new Date(result.scan_timestamp).toLocaleString()}</span>
                            </div>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        {/* Limit Dropdown */}
                        <div className="relative">
                            <select
                                value={scanLimit}
                                onChange={(e) => setScanLimit(Number(e.target.value))}
                                className={`text-xs font-bold py-2 pl-3 pr-8 rounded-lg appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/50 ${isDark
                                    ? "bg-slate-800 border border-slate-600 text-slate-300 hover:bg-slate-700"
                                    : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 shadow-sm"
                                    }`}
                            >
                                <option value={50}>50 Items</option>
                                <option value={100}>100 Items</option>
                                <option value={500}>500 Items</option>
                                <option value={5000}>5000 Items</option>
                            </select>
                            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-500">
                                <ChevronDown className="h-3 w-3" />
                            </div>
                        </div>

                        <button
                            onClick={() => setShowHistory(true)}
                            className={`p-2 rounded-lg transition-colors ${isDark ? "hover:bg-slate-700 text-slate-400" : "hover:bg-slate-100 text-slate-500"}`}
                            title="View Scan History"
                        >
                            <History className="w-5 h-5" />
                        </button>
                        <button
                            onClick={runScan}
                            disabled={loading}
                            className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all active:scale-95 ${isDark
                                ? "bg-blue-600 hover:bg-blue-500 text-white disabled:bg-slate-700 disabled:text-slate-500"
                                : "bg-blue-600 hover:bg-blue-700 text-white disabled:bg-slate-100 disabled:text-slate-400"
                                }`}
                        >
                            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                            {loading ? "Diagnosing..." : "Run Diagnostic"}
                        </button>
                    </div>
                </div>

                <div className="p-6">
                    {!result && !loading ? (
                        <div className={`p-12 rounded-xl border border-dashed text-center flex flex-col items-center ${isDark ? "border-slate-700 bg-slate-900/50" : "border-slate-200 bg-slate-50/50"}`}>
                            <Database className={`w-16 h-16 mb-4 opacity-20 ${isDark ? "text-white" : "text-slate-900"}`} />
                            <h4 className={`text-lg font-semibold mb-2 ${isDark ? "text-slate-300" : "text-slate-700"}`}>Initial Diagnosis Required</h4>
                            <p className={`text-sm mb-8 max-w-sm mx-auto ${isDark ? "text-slate-500" : "text-slate-500"}`}>
                                The AI Doctor needs a full system scan to identify bloat, connection issues, and configuration bottlenecks.
                            </p>
                        </div>
                    ) : result ? (
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                            {/* Score & AI Triage */}
                            <div className="lg:col-span-4 flex flex-col items-center">
                                <div className={`w-full p-8 rounded-2xl border ${getHealthBgColor(result.health_score)} transition-colors duration-500 relative overflow-hidden`}>
                                    <div className="flex flex-col items-center justify-center relative z-10 w-full">
                                        <HealthScoreGauge score={result.health_score} loading={loading} />
                                        <div className="mt-6 text-center w-full relative">
                                            <div className="flex items-center justify-center gap-1">
                                                <span className={`text-xs uppercase tracking-widest font-black ${isDark ? "text-slate-500" : "text-slate-400"}`}>Health Score</span>
                                                <button
                                                    onMouseEnter={() => setShowMethodology(true)}
                                                    onMouseLeave={() => setShowMethodology(false)}
                                                    className="p-1 rounded-full hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                                                >
                                                    <Info className="w-3.5 h-3.5 opacity-40 hover:opacity-100 transition-opacity" />
                                                </button>

                                                {showMethodology && result.score_breakdown && (
                                                    <div className={`absolute bottom-full left-1/2 -translate-x-1/2 mb-4 w-64 p-4 rounded-xl shadow-2xl z-[100] border backdrop-blur-md animate-in fade-in zoom-in-95 duration-200 ${isDark ? "bg-slate-900/95 border-slate-700 text-slate-300" : "bg-white/95 border-slate-200 text-slate-700"
                                                        }`}>
                                                        <p className="text-[10px] uppercase font-bold text-center opacity-60 mb-3 border-b border-black/10 dark:border-white/10 pb-2">Score Methodology</p>
                                                        <ul className="space-y-2">
                                                            {result.score_breakdown.map((point, idx) => (
                                                                <li key={idx} className="text-[10px] leading-relaxed flex items-start gap-2">
                                                                    <div className="mt-1 w-1 h-1 rounded-full bg-red-500 flex-shrink-0" />
                                                                    <span>{point}</span>
                                                                </li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}
                                            </div>
                                            <p className={`text-sm mt-1 font-medium ${isDark ? "text-slate-300" : "text-slate-600"}`}>
                                                {result.health_score >= 80 ? "Peak Condition" : result.health_score >= 50 ? "Needs Attention" : "Critical State"}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Doctor's Primary Notes (AI Triage) */}
                            <div className="lg:col-span-8">
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className={`text-xs uppercase tracking-[0.2em] font-black ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                        Recent Findings ({result.issues?.length || 0})
                                    </h3>
                                    <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-500 font-medium">
                                        AI Prioritized
                                    </span>
                                </div>

                                {(!result.issues || result.issues.length === 0) ? (
                                    <div className={`h-[300px] flex flex-col items-center justify-center rounded-2xl border border-dashed ${isDark ? "border-slate-700 text-slate-500 bg-slate-900/20" : "border-slate-200 text-slate-400 bg-slate-50/50"}`}>
                                        <div className="flex items-center justify-center w-12 h-12 rounded-full bg-green-500/10 mb-4 animate-pulse">
                                            <CheckCircle2 className="w-6 h-6 text-green-500" />
                                        </div>
                                        <p className="text-base font-semibold text-slate-800 dark:text-slate-200">System Healthy</p>
                                        <p className="text-xs mt-2 opacity-70">No priority issues requiring immediate attention.</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                                        {result.issues.map((issue, i) => (
                                            <IssueCard key={i} issue={issue} onAction={handleIssueAction} />
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : null}
                </div>
            </div>

            {/* Detailed Stats Cards */}
            {result && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Bloat Card */}
                    <div
                        onClick={() => setExpandedSection(expandedSection === "bloat" ? null : "bloat")}
                        className={`${cardClass} cursor-pointer hover:ring-2 ring-blue-500/20 transition-all ${expandedSection === "bloat" ? "ring-2 ring-blue-500" : ""} group`}
                    >
                        <div className="p-4 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className={`p-2 rounded-lg transition-colors ${isDark ? "bg-red-500/10 group-hover:bg-red-500/20" : "bg-red-50 group-hover:bg-red-100"}`}>
                                    <Database className={`w-5 h-5 ${isDark ? "text-red-400" : "text-red-500"}`} />
                                </div>
                                <div>
                                    <p className={`text-xs font-bold uppercase tracking-wider ${isDark ? "text-slate-500" : "text-slate-400"}`}>Table Bloat</p>
                                    <div className="flex items-baseline gap-1">
                                        <span className={`text-xl font-bold ${result.summary.total_bloated_tables > 0 ? "text-red-500" : isDark ? "text-white" : "text-slate-800"}`}>
                                            {result.summary.total_bloated_tables}
                                        </span>
                                        <span className={`text-xs ${isDark ? "text-slate-400" : "text-slate-400"}`}>Alerts</span>
                                    </div>
                                </div>
                            </div>
                            {expandedSection === "bloat" ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                        </div>
                    </div>

                    {/* Unused Indexes Card */}
                    <div
                        onClick={() => setExpandedSection(expandedSection === "indexes" ? null : "indexes")}
                        className={`${cardClass} cursor-pointer hover:ring-2 ring-blue-500/20 transition-all ${expandedSection === "indexes" ? "ring-2 ring-blue-500" : ""} group`}
                    >
                        <div className="p-4 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className={`p-2 rounded-lg transition-colors ${isDark ? "bg-yellow-500/10 group-hover:bg-yellow-500/20" : "bg-yellow-50 group-hover:bg-yellow-100"}`}>
                                    <FileX className={`w-5 h-5 ${isDark ? "text-yellow-400" : "text-yellow-500"}`} />
                                </div>
                                <div>
                                    <p className={`text-xs font-bold uppercase tracking-wider ${isDark ? "text-slate-500" : "text-slate-400"}`}>Unused Indexes</p>
                                    <div className="flex items-baseline gap-1">
                                        <span className={`text-xl font-bold ${result.summary.total_unused_indexes > 0 ? "text-yellow-600" : isDark ? "text-white" : "text-slate-800"}`}>
                                            {result.summary.total_unused_indexes}
                                        </span>
                                        <span className={`text-xs ${isDark ? "text-slate-400" : "text-slate-400"}`}>Candidates</span>
                                    </div>
                                </div>
                            </div>
                            {expandedSection === "indexes" ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                        </div>
                    </div>

                    {/* Config Card */}
                    <div
                        onClick={() => setExpandedSection(expandedSection === "config" ? null : "config")}
                        className={`${cardClass} cursor-pointer hover:ring-2 ring-blue-500/20 transition-all ${expandedSection === "config" ? "ring-2 ring-blue-500" : ""} group`}
                    >
                        <div className="p-4 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className={`p-2 rounded-lg transition-colors ${isDark ? "bg-blue-500/10 group-hover:bg-blue-500/20" : "bg-blue-50 group-hover:bg-blue-100"}`}>
                                    <Settings className={`w-5 h-5 ${isDark ? "text-blue-400" : "text-blue-500"}`} />
                                </div>
                                <div>
                                    <p className={`text-xs font-bold uppercase tracking-wider ${isDark ? "text-slate-500" : "text-slate-400"}`}>Config Checks</p>
                                    <div className="flex items-baseline gap-1">
                                        <span className={`text-xl font-bold ${result.summary.total_config_issues > 0 ? "text-blue-500" : isDark ? "text-white" : "text-slate-800"}`}>
                                            {result.summary.total_config_issues}
                                        </span>
                                        <span className={`text-xs ${isDark ? "text-slate-400" : "text-slate-400"}`}>Notices</span>
                                    </div>
                                </div>
                            </div>
                            {expandedSection === "config" ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                        </div>
                    </div>
                </div>
            )}

            {/* Drill-down View */}
            {expandedSection && result && (
                <div className={`${cardClass} animate-in fade-in slide-in-from-top-4 duration-300 p-5`}>
                    {/* Reuse existing logic for expanded view content but polished - kept logic same for brevity in this replace but imagine cleaner headers */}
                    <div className="flex items-center justify-between mb-4">
                        <h3 className={`font-bold ${isDark ? "text-white" : "text-slate-900"}`}>
                            {expandedSection === "bloat" && "Table Bloat Analysis"}
                            {expandedSection === "indexes" && "Unused Index Candidates"}
                            {expandedSection === "config" && "Configuration Review"}
                        </h3>
                        <button onClick={() => setExpandedSection(null)} className={`text-xs hover:underline ${isDark ? "text-slate-500" : "text-slate-400"}`}>Close</button>
                    </div>
                    {/* Content rendering logic remains similar to previous version basically */}
                    <div className="grid grid-cols-1 gap-3 max-h-[500px] overflow-y-auto custom-scrollbar">
                        {expandedSection === "bloat" && result.table_bloat.issues.map((issue, idx) => (
                            <div key={idx} className={`p-4 rounded-lg border ${isDark ? "bg-slate-900/30 border-slate-700" : "bg-slate-50 border-slate-200"}`}>
                                <div className="flex justify-between items-start">
                                    <div>
                                        <p className="font-mono text-sm font-bold text-blue-500">{issue.schema}.{issue.table}</p>
                                        <p className={`text-xs mt-1 ${isDark ? "text-slate-400" : "text-slate-500"}`}>Dead Ratio: <span className={issue.dead_ratio > 20 ? "text-red-500 font-bold" : ""}>{issue.dead_ratio}%</span></p>
                                    </div>
                                    <span className={`text-[10px] uppercase font-bold px-2 py-1 rounded ${getSeverityColor(issue.severity)}`}>{issue.severity}</span>
                                </div>
                                <div className={`mt-2 p-2 rounded text-xs font-mono font-medium ${isDark ? "bg-black/20 text-slate-300" : "bg-white border text-slate-600"}`}>
                                    {issue.recommendation}
                                </div>
                            </div>
                        ))}
                        {expandedSection === "indexes" && result.index_bloat.unused_indexes.map((issue, idx) => (
                            <div key={idx} className={`p-4 rounded-lg border ${isDark ? "bg-slate-900/30 border-slate-700" : "bg-slate-50 border-slate-200"}`}>
                                <div className="flex justify-between items-start">
                                    <div>
                                        <p className="font-mono text-sm font-bold text-yellow-500">{issue.index}</p>
                                        <p className={`text-xs mt-1 ${isDark ? "text-slate-400" : "text-slate-500"}`}>Size: {issue.size} • Scans: 0</p>
                                    </div>
                                    <button onClick={() => setShowSqlModal(issue.recommendation)} className="text-xs bg-red-500 text-white px-2 py-1 rounded hover:bg-red-600 transition">Drop</button>
                                </div>
                            </div>
                        ))}
                        {expandedSection === "config" && result.config_issues.issues.map((issue, idx) => (
                            <div key={idx} className={`p-4 rounded-lg border ${isDark ? "bg-slate-900/30 border-slate-700" : "bg-slate-50 border-slate-200"}`}>
                                <div className="flex justify-between items-start mb-2">
                                    <div>
                                        <p className={`font-bold text-sm ${isDark ? "text-white" : "text-slate-900"}`}>{issue.setting}</p>
                                        <p className="text-xs text-red-500 mt-0.5">{issue.issue}</p>
                                    </div>
                                    <span className={`text-[10px] font-mono ${isDark ? "text-slate-400" : "text-slate-500"}`}>Current: {issue.current_value}</span>
                                </div>
                                <div className={`relative group mt-3 p-3 rounded-lg border ${isDark ? "bg-black/40 border-slate-700" : "bg-slate-100 border-slate-200"}`}>
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-[10px] uppercase font-bold text-blue-500">Fix SQL</span>
                                        <button
                                            onClick={() => {
                                                const sql = generateConfigSql(issue.setting, issue.recommendation);
                                                navigator.clipboard.writeText(sql);
                                                toast.success("SQL copied to clipboard");
                                            }}
                                            className="p-1.5 rounded-md hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
                                            title="Copy SQL"
                                        >
                                            <Clipboard className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                    <pre className="text-[11px] font-mono text-slate-400 overflow-x-auto">
                                        {generateConfigSql(issue.setting, issue.recommendation)}
                                    </pre>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* History Modal/Drawer */}
            {showHistory && (
                <div className="fixed inset-0 z-[50] flex justify-end bg-black/20 backdrop-blur-sm animate-in fade-in">
                    <div className={`w-full max-w-md h-full shadow-2xl p-6 flex flex-col ${isDark ? "bg-slate-900 border-l border-slate-700" : "bg-white border-l border-slate-200"} animate-in slide-in-from-right duration-300`}>
                        <div className="flex items-center justify-between mb-6">
                            <h3 className={`font-bold text-lg ${isDark ? "text-white" : "text-slate-900"}`}>Diagnostic History</h3>
                            <button onClick={() => setShowHistory(false)} className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto custom-scrollbar space-y-3">
                            {loadingHistory ? (
                                <div className="text-center py-10 opacity-50">Loading history...</div>
                            ) : history.length === 0 ? (
                                <div className="text-center py-10 opacity-50">No scan history available.</div>
                            ) : (
                                history.map((scan, idx) => (
                                    <div
                                        key={scan.id || idx}
                                        onClick={() => { setResult(scan); setShowHistory(false); }}
                                        className={`p-4 rounded-xl border cursor-pointer hover:ring-2 ring-blue-500/20 transition-all ${isDark ? "bg-slate-800 border-slate-700" : "bg-slate-50 border-slate-200"}`}
                                    >
                                        <div className="flex justify-between items-center mb-2">
                                            <span className={`font-bold ${scan.health_score >= 80 ? "text-green-500" : scan.health_score >= 50 ? "text-yellow-500" : "text-red-500"}`}>
                                                Score: {scan.health_score}
                                            </span>
                                            <span className="text-xs opacity-50">{new Date(scan.scan_timestamp).toLocaleDateString()}</span>
                                        </div>
                                        <div className="flex gap-2 text-[10px] opacity-60 uppercase font-bold">
                                            <span>{scan.issues.length} Issues</span>
                                            <span>•</span>
                                            <span>{scan.summary.total_bloated_tables} Bloat</span>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* SQL Modal */}
            {showSqlModal && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
                    <div className={`w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden border ${isDark ? "bg-slate-900 border-slate-700" : "bg-white border-slate-200"}`}>
                        <div className={`flex items-center justify-between p-5 border-b ${isDark ? "border-slate-800" : "border-slate-200"}`}>
                            <div>
                                <h3 className={`font-bold text-lg ${isDark ? "text-white" : "text-slate-800"}`}>Doctor&apos;s Prescription</h3>
                                <p className="text-xs text-slate-500">Execute this SQL to resolve the identified issue</p>
                            </div>
                            <button onClick={() => setShowSqlModal(null)} className={`p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <div className="p-6">
                            <div className="relative group">
                                <pre className={`p-5 rounded-xl text-sm font-mono overflow-x-auto border ${isDark ? "bg-black/40 text-blue-300 border-slate-700" : "bg-slate-50 text-blue-800 border-slate-200"}`}>
                                    {showSqlModal}
                                </pre>
                                <button
                                    onClick={copyToClipboard}
                                    className="absolute top-4 right-4 p-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white shadow-lg transition-all active:scale-95"
                                >
                                    {copied ? <Check className="w-4.5 h-4.5" /> : <Clipboard className="w-4.5 h-4.5" />}
                                </button>
                            </div>

                            <div className={`mt-6 p-4 rounded-xl flex items-start gap-4 ${isDark ? "bg-yellow-500/5 border border-yellow-500/20" : "bg-yellow-50 border border-yellow-200"}`}>
                                <AlertTriangle className="w-6 h-6 text-yellow-500 flex-shrink-0" />
                                <p className={`text-xs leading-relaxed ${isDark ? "text-yellow-200/70" : "text-yellow-800/80"}`}>
                                    <strong>Caution:</strong> This action modifies your database schema or configuration.
                                    Always test in a staging environment before running on production.
                                    Ensure you have a recent backup available.
                                </p>
                            </div>
                        </div>
                        <div className={`p-5 flex justify-end gap-3 ${isDark ? "bg-slate-800/50 border-t border-slate-800" : "bg-slate-50 border-t border-slate-200"}`}>
                            <button
                                onClick={() => setShowSqlModal(null)}
                                className={`px-5 py-2 rounded-xl text-sm font-bold ${isDark ? "text-slate-400 hover:text-white" : "text-slate-500 hover:text-slate-800"}`}
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
