"use client";

import { useState, useEffect } from "react";
import { useAppStore } from "@/store/appStore";
import { Activity, AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, RefreshCw, Database, Settings, FileX } from "lucide-react";
import { toast } from "sonner";

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

interface HealthScanResult {
    scan_timestamp: string;
    health_score: number;
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

// TODO: Add AI analysis toggle button that calls /api/ai/analyze-health
// This would provide AI-powered insights on top of rule-based health checks
export function HealthScanWidget() {
    const { theme } = useAppStore();
    const isDark = theme === "dark";
    const [scanResult, setScanResult] = useState<HealthScanResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

    const fetchLatestScan = async () => {
        try {
            const res = await fetch(`${apiUrl}/api/health/latest`);
            if (res.ok) {
                const data = await res.json();
                setScanResult(data);
            } else if (res.status !== 404) {
                throw new Error("Failed to fetch scan results");
            }
        } catch (error) {
            console.error("Failed to fetch latest scan:", error);
        }
    };

    useEffect(() => {
        fetchLatestScan();
    }, []);

    const triggerScan = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${apiUrl}/api/health/scan`, {
                method: "POST",
            });

            if (!res.ok) {
                const errorData = await res.json().catch(() => ({ error: "Scan failed" }));
                throw new Error(errorData.error || "Health scan failed");
            }

            const data = await res.json();
            setScanResult(data);
            toast.success("Health scan completed");
        } catch (error) {
            console.error("Health scan error:", error);
            toast.error(error instanceof Error ? error.message : "Health scan failed");
        } finally {
            setLoading(false);
        }
    };

    const toggleSection = (section: string) => {
        const newExpanded = new Set(expandedSections);
        if (newExpanded.has(section)) {
            newExpanded.delete(section);
        } else {
            newExpanded.add(section);
        }
        setExpandedSections(newExpanded);
    };

    const getHealthColor = (score: number) => {
        if (score >= 80) return "text-green-500";
        if (score >= 50) return "text-yellow-500";
        return "text-red-500";
    };

    const getHealthBgColor = (score: number) => {
        if (score >= 80) return "bg-green-500/10 border-green-500/20";
        if (score >= 50) return "bg-yellow-500/10 border-yellow-500/20";
        return "bg-red-500/10 border-red-500/20";
    };

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case "high":
                return "bg-red-500/20 text-red-400 border-red-500/40";
            case "medium":
                return "bg-yellow-500/20 text-yellow-400 border-yellow-500/40";
            default:
                return "bg-blue-500/20 text-blue-400 border-blue-500/40";
        }
    };

    const formatTimestamp = (timestamp: string) => {
        try {
            const date = new Date(timestamp);
            return date.toLocaleString();
        } catch {
            return timestamp;
        }
    };

    const cardClass = `rounded-xl border p-6 ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`;

    if (!scanResult && !loading) {
        return (
            <div className={cardClass}>
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <Activity className={`w-5 h-5 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                        <h2 className={`text-lg font-semibold ${isDark ? "text-white" : "text-slate-800"}`}>
                            Database Health Scan
                        </h2>
                    </div>
                </div>
                <div className={`text-center py-8 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                    <Database className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm mb-4">No health scan has been run yet.</p>
                    <button
                        onClick={triggerScan}
                        disabled={loading}
                        className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium ${
                            isDark
                                ? "bg-blue-600 hover:bg-blue-700 text-white"
                                : "bg-blue-600 hover:bg-blue-700 text-white"
                        } disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                        <Activity className="w-4 h-4" />
                        Run Health Scan
                    </button>
                </div>
            </div>
        );
    }

    if (scanResult?.error) {
        return (
            <div className={cardClass}>
                <div className="flex items-center gap-3 mb-4">
                    <AlertTriangle className="w-5 h-5 text-red-500" />
                    <h2 className={`text-lg font-semibold ${isDark ? "text-white" : "text-slate-800"}`}>
                        Health Scan Error
                    </h2>
                </div>
                <p className={`text-sm ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                    {scanResult.error}
                </p>
                <button
                    onClick={triggerScan}
                    disabled={loading}
                    className={`mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium ${
                        isDark
                            ? "bg-blue-600 hover:bg-blue-700 text-white"
                            : "bg-blue-600 hover:bg-blue-700 text-white"
                    } disabled:opacity-50`}
                >
                    <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                    Retry Scan
                </button>
            </div>
        );
    }

    const healthScore = scanResult?.health_score ?? 0;

    return (
        <div className={cardClass}>
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <Activity className={`w-5 h-5 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                    <div>
                        <h2 className={`text-lg font-semibold ${isDark ? "text-white" : "text-slate-800"}`}>
                            Database Health Scan
                        </h2>
                        {scanResult && (
                            <p className={`text-xs mt-0.5 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                Last scan: {formatTimestamp(scanResult.scan_timestamp)}
                            </p>
                        )}
                    </div>
                </div>
                <button
                    onClick={triggerScan}
                    disabled={loading}
                    className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium ${
                        isDark
                            ? "bg-slate-700 hover:bg-slate-600 text-slate-200"
                            : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                    <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                    {loading ? "Scanning..." : "Scan Now"}
                </button>
            </div>

            {loading && !scanResult ? (
                <div className="flex items-center justify-center py-12">
                    <div className="flex flex-col items-center gap-3">
                        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                        <span className={`text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                            Running health scan...
                        </span>
                    </div>
                </div>
            ) : scanResult ? (
                <>
                    {/* Health Score */}
                    <div className={`mb-6 p-6 rounded-lg border ${getHealthBgColor(healthScore)}`}>
                        <div className="flex items-center justify-between">
                            <div>
                                <p className={`text-sm font-medium mb-1 ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                                    Overall Health Score
                                </p>
                                <div className="flex items-baseline gap-2">
                                    <span className={`text-4xl font-bold ${getHealthColor(healthScore)}`}>
                                        {healthScore}
                                    </span>
                                    <span className={`text-lg ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                        / 100
                                    </span>
                                </div>
                            </div>
                            {healthScore >= 80 ? (
                                <CheckCircle2 className="w-12 h-12 text-green-500" />
                            ) : (
                                <AlertTriangle className="w-12 h-12 text-yellow-500" />
                            )}
                        </div>
                    </div>

                    {/* Summary Cards */}
                    <div className="grid grid-cols-3 gap-4 mb-6">
                        <div className={`p-4 rounded-lg border ${isDark ? "bg-slate-700/50 border-slate-600" : "bg-slate-50 border-slate-200"}`}>
                            <div className="flex items-center gap-2 mb-1">
                                <Database className={`w-4 h-4 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                <span className={`text-xs font-medium ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                                    Bloated Tables
                                </span>
                            </div>
                            <p className={`text-2xl font-bold ${scanResult.summary.total_bloated_tables > 0 ? "text-red-500" : isDark ? "text-white" : "text-slate-800"}`}>
                                {scanResult.summary.total_bloated_tables}
                            </p>
                        </div>
                        <div className={`p-4 rounded-lg border ${isDark ? "bg-slate-700/50 border-slate-600" : "bg-slate-50 border-slate-200"}`}>
                            <div className="flex items-center gap-2 mb-1">
                                <FileX className={`w-4 h-4 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                <span className={`text-xs font-medium ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                                    Unused Indexes
                                </span>
                            </div>
                            <p className={`text-2xl font-bold ${scanResult.summary.total_unused_indexes > 0 ? "text-yellow-500" : isDark ? "text-white" : "text-slate-800"}`}>
                                {scanResult.summary.total_unused_indexes}
                            </p>
                        </div>
                        <div className={`p-4 rounded-lg border ${isDark ? "bg-slate-700/50 border-slate-600" : "bg-slate-50 border-slate-200"}`}>
                            <div className="flex items-center gap-2 mb-1">
                                <Settings className={`w-4 h-4 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                <span className={`text-xs font-medium ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                                    Config Issues
                                </span>
                            </div>
                            <p className={`text-2xl font-bold ${scanResult.summary.total_config_issues > 0 ? "text-orange-500" : isDark ? "text-white" : "text-slate-800"}`}>
                                {scanResult.summary.total_config_issues}
                            </p>
                        </div>
                    </div>

                    {/* Expandable Sections */}
                    {scanResult.table_bloat.issues.length > 0 && (
                        <div className={`mb-4 rounded-lg border ${isDark ? "bg-slate-700/30 border-slate-600" : "bg-slate-50 border-slate-200"}`}>
                            <button
                                onClick={() => toggleSection("bloat")}
                                className="w-full flex items-center justify-between p-4"
                            >
                                <div className="flex items-center gap-2">
                                    <Database className={`w-4 h-4 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                    <span className={`font-medium ${isDark ? "text-white" : "text-slate-800"}`}>
                                        Table Bloat Issues ({scanResult.table_bloat.issues.length})
                                    </span>
                                </div>
                                {expandedSections.has("bloat") ? (
                                    <ChevronUp className={`w-4 h-4 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                ) : (
                                    <ChevronDown className={`w-4 h-4 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                )}
                            </button>
                            {expandedSections.has("bloat") && (
                                <div className="px-4 pb-4 space-y-3">
                                    {scanResult.table_bloat.issues.map((issue, idx) => (
                                        <div
                                            key={idx}
                                            className={`p-3 rounded border ${isDark ? "bg-slate-800 border-slate-600" : "bg-white border-slate-200"}`}
                                        >
                                            <div className="flex items-start justify-between mb-2">
                                                <div>
                                                    <span className={`font-mono text-sm font-medium ${isDark ? "text-white" : "text-slate-800"}`}>
                                                        {issue.schema}.{issue.table}
                                                    </span>
                                                    <span className={`ml-2 px-2 py-0.5 rounded text-xs border ${getSeverityColor(issue.severity)}`}>
                                                        {issue.severity}
                                                    </span>
                                                </div>
                                                <span className={`text-sm font-medium ${isDark ? "text-slate-300" : "text-slate-700"}`}>
                                                    {issue.dead_ratio.toFixed(1)}% dead
                                                </span>
                                            </div>
                                            <div className={`text-xs mb-2 ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                                                {issue.dead_tuples.toLocaleString()} dead / {issue.live_tuples.toLocaleString()} live tuples
                                                {issue.vacuum_overdue && (
                                                    <span className="ml-2 text-red-500 font-medium">• Vacuum overdue</span>
                                                )}
                                            </div>
                                            <p className={`text-xs ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                                                {issue.recommendation}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {scanResult.index_bloat.unused_indexes.length > 0 && (
                        <div className={`mb-4 rounded-lg border ${isDark ? "bg-slate-700/30 border-slate-600" : "bg-slate-50 border-slate-200"}`}>
                            <button
                                onClick={() => toggleSection("indexes")}
                                className="w-full flex items-center justify-between p-4"
                            >
                                <div className="flex items-center gap-2">
                                    <FileX className={`w-4 h-4 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                    <span className={`font-medium ${isDark ? "text-white" : "text-slate-800"}`}>
                                        Unused Indexes ({scanResult.index_bloat.unused_indexes.length})
                                    </span>
                                </div>
                                {expandedSections.has("indexes") ? (
                                    <ChevronUp className={`w-4 h-4 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                ) : (
                                    <ChevronDown className={`w-4 h-4 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                )}
                            </button>
                            {expandedSections.has("indexes") && (
                                <div className="px-4 pb-4 space-y-3">
                                    {scanResult.index_bloat.unused_indexes.map((issue, idx) => (
                                        <div
                                            key={idx}
                                            className={`p-3 rounded border ${isDark ? "bg-slate-800 border-slate-600" : "bg-white border-slate-200"}`}
                                        >
                                            <div className="flex items-start justify-between mb-2">
                                                <div>
                                                    <span className={`font-mono text-sm font-medium ${isDark ? "text-white" : "text-slate-800"}`}>
                                                        {issue.schema}.{issue.table}.{issue.index}
                                                    </span>
                                                </div>
                                                <span className={`text-sm font-medium ${isDark ? "text-slate-300" : "text-slate-700"}`}>
                                                    {issue.size}
                                                </span>
                                            </div>
                                            <div className={`text-xs mb-2 ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                                                {issue.scans} scans • {issue.tuples_read.toLocaleString()} tuples read
                                            </div>
                                            <p className={`text-xs ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                                                {issue.recommendation}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {scanResult.config_issues.issues.length > 0 && (
                        <div className={`rounded-lg border ${isDark ? "bg-slate-700/30 border-slate-600" : "bg-slate-50 border-slate-200"}`}>
                            <button
                                onClick={() => toggleSection("config")}
                                className="w-full flex items-center justify-between p-4"
                            >
                                <div className="flex items-center gap-2">
                                    <Settings className={`w-4 h-4 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                    <span className={`font-medium ${isDark ? "text-white" : "text-slate-800"}`}>
                                        Configuration Issues ({scanResult.config_issues.issues.length})
                                    </span>
                                </div>
                                {expandedSections.has("config") ? (
                                    <ChevronUp className={`w-4 h-4 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                ) : (
                                    <ChevronDown className={`w-4 h-4 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                )}
                            </button>
                            {expandedSections.has("config") && (
                                <div className="px-4 pb-4 space-y-3">
                                    {scanResult.config_issues.issues.map((issue, idx) => (
                                        <div
                                            key={idx}
                                            className={`p-3 rounded border ${isDark ? "bg-slate-800 border-slate-600" : "bg-white border-slate-200"}`}
                                        >
                                            <div className="flex items-start justify-between mb-2">
                                                <div>
                                                    <span className={`font-mono text-sm font-medium ${isDark ? "text-white" : "text-slate-800"}`}>
                                                        {issue.setting}
                                                    </span>
                                                    <span className={`ml-2 px-2 py-0.5 rounded text-xs border ${getSeverityColor(issue.severity)}`}>
                                                        {issue.severity}
                                                    </span>
                                                </div>
                                                <span className={`text-sm font-medium ${isDark ? "text-slate-300" : "text-slate-700"}`}>
                                                    {issue.current_value}
                                                </span>
                                            </div>
                                            <p className={`text-xs mb-1 ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                                                {issue.issue}
                                            </p>
                                            <p className={`text-xs ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                                                {issue.recommendation}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {scanResult.summary.total_bloated_tables === 0 &&
                        scanResult.summary.total_unused_indexes === 0 &&
                        scanResult.summary.total_config_issues === 0 && (
                            <div className={`text-center py-8 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                <CheckCircle2 className="w-12 h-12 mx-auto mb-3 text-green-500 opacity-50" />
                                <p className="text-sm">No issues detected. Database is healthy!</p>
                            </div>
                        )}
                </>
            ) : null}
        </div>
    );
}

