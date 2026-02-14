"use client";

import { useState, useRef, useEffect } from "react";
import { useAppStore } from "@/store/appStore";
import { useCartStore } from "@/store/cartStore";
import {
    Database,
    RefreshCw,
    AlertTriangle,
    Info,
    CheckCircle2,
    ChevronDown,
    ChevronUp,
    Trash2,
    Eye,
    ShieldCheck,
    TrendingDown,
    HardDrive,
    ShoppingCart,
    Check,
    ArrowRight,
    Clock,
    HelpCircle
} from "lucide-react";
import { toast } from "sonner";

// ── InfoTip: hover popover for explaining terminology ──
function InfoTip({ text, isDark }: { text: string; isDark: boolean }) {
    const [show, setShow] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) setShow(false);
        };
        if (show) document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [show]);

    return (
        <div className="relative inline-flex" ref={ref}>
            <button
                onClick={(e) => { e.stopPropagation(); setShow(!show); }}
                onMouseEnter={() => setShow(true)}
                onMouseLeave={() => setShow(false)}
                className="text-slate-400 hover:text-blue-400 transition-colors"
            >
                <HelpCircle className="w-3 h-3" />
            </button>
            {show && (
                <div className={`absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 rounded-lg text-xs leading-relaxed max-w-[260px] w-max shadow-lg border ${
                    isDark
                        ? "bg-slate-700 border-slate-600 text-slate-200"
                        : "bg-white border-slate-200 text-slate-700"
                }`}>
                    {text}
                    <div className={`absolute top-full left-1/2 -translate-x-1/2 w-2 h-2 rotate-45 ${
                        isDark ? "bg-slate-700 border-r border-b border-slate-600" : "bg-white border-r border-b border-slate-200"
                    }`} />
                </div>
            )}
        </div>
    );
}

interface ScoreBreakdown {
    scan_score: number;
    cost_score: number;
    size_score: number;
    constraint_bonus: number;
}

interface IndexScore {
    schema_name: string;
    table_name: string;
    index_name: string;
    usefulness_score: number;
    recommended_stage: "active" | "monitoring" | "ready_to_disable" | "ready_to_drop";
    idx_scan: number;
    scan_rate_per_day: number;
    size_bytes: number;
    size_pretty: string;
    total_writes: number;
    write_overhead_ratio: number;
    is_primary_key: boolean;
    is_unique: boolean;
    backs_constraint: boolean;
    constraint_type: string | null;
    score_breakdown: ScoreBreakdown;
    confidence_note: string | null;
}

interface AnalysisResult {
    success: boolean;
    stats_age_days: number;
    stats_reliable: boolean;
    total_indexes: number;
    summary: {
        drop_candidates: number;
        disable_candidates: number;
        monitoring: number;
        healthy: number;
        total_reclaimable_bytes: number;
        total_reclaimable_pretty: string;
    };
    indexes: IndexScore[];
}

interface DecommissionEntry {
    id: number;
    database_name: string;
    schema_name: string;
    table_name: string;
    index_name: string;
    stage: string;
    usefulness_score: number;
    idx_scan_at_start: number;
    idx_scan_latest: number;
    size_bytes: number;
    started_at: string;
    stage_changed_at: string;
    notes: string;
}

type ViewMode = "analysis" | "tracking";

export function UnusedIndexes() {
    const { theme } = useAppStore();
    const { addItem, isInCart } = useCartStore();
    const isDark = theme === "dark";

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [tracking, setTracking] = useState<DecommissionEntry[]>([]);
    const [loadingTracking, setLoadingTracking] = useState(false);
    const [expandedIndex, setExpandedIndex] = useState<string | null>(null);
    const [filter, setFilter] = useState<"all" | "drop" | "disable" | "monitoring" | "active">("all");
    const [showStructural, setShowStructural] = useState(false);
    const [viewMode, setViewMode] = useState<ViewMode>("analysis");

    const [cacheAge, setCacheAge] = useState<number | null>(null);

    const apiUrl = import.meta.env.VITE_API_URL || "";

    // Auto-load cached results on mount
    useEffect(() => {
        fetchCached();
    }, []);

    const fetchCached = async () => {
        try {
            const res = await fetch(`${apiUrl}/api/health/unused-indexes`);
            const data = await res.json();
            if (data.success) {
                setResult(data);
                setCacheAge(data._cache_age_seconds ?? null);
            }
        } catch {
            // Silently fail — user can manually scan
        }
    };

    const runAnalysis = async (refresh = true) => {
        setLoading(true);
        try {
            const res = await fetch(`${apiUrl}/api/health/unused-indexes?refresh=${refresh}`);
            const data = await res.json();
            if (data.success) {
                setResult(data);
                setCacheAge(data._cache_age_seconds ?? null);
                toast.success(`Analyzed ${data.total_indexes} indexes`);
            } else {
                toast.error(data.error || "Analysis failed");
            }
        } catch (e) {
            toast.error("Failed to analyze indexes");
        } finally {
            setLoading(false);
        }
    };

    const fetchTracking = async () => {
        setLoadingTracking(true);
        try {
            const res = await fetch(`${apiUrl}/api/health/decommission/tracking`);
            const data = await res.json();
            if (data.success) {
                setTracking(data.entries);
            }
        } catch (e) {
            toast.error("Failed to fetch tracking data");
        } finally {
            setLoadingTracking(false);
        }
    };

    const startMonitoring = async (indexes: IndexScore[]) => {
        try {
            const res = await fetch(`${apiUrl}/api/health/decommission/start`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    indexes: indexes.map((i) => ({
                        schema_name: i.schema_name,
                        table_name: i.table_name,
                        index_name: i.index_name,
                        usefulness_score: i.usefulness_score,
                        idx_scan: i.idx_scan,
                        size_bytes: i.size_bytes,
                        write_overhead_ratio: i.write_overhead_ratio,
                        scan_rate_per_day: i.scan_rate_per_day,
                        is_primary_key: i.is_primary_key,
                        backs_constraint: i.backs_constraint,
                        constraint_type: i.constraint_type,
                    })),
                    database_name: "current", // Will be resolved server-side
                }),
            });
            const data = await res.json();
            if (data.success) {
                toast.success(`Started monitoring ${data.tracked} indexes`);
                if (data.skipped_constraints > 0) {
                    toast.info(`Skipped ${data.skipped_constraints} constraint-backed indexes`);
                }
                fetchTracking();
            }
        } catch (e) {
            toast.error("Failed to start monitoring");
        }
    };

    const updateStage = async (id: number, newStage: string, notes: string = "") => {
        try {
            const res = await fetch(`${apiUrl}/api/health/decommission/update-stage`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ decommission_id: id, new_stage: newStage, notes }),
            });
            const data = await res.json();
            if (data.success) {
                toast.success(`Stage updated to ${newStage}`);
                fetchTracking();
            }
        } catch (e) {
            toast.error("Failed to update stage");
        }
    };

    const refreshSnapshots = async () => {
        try {
            const res = await fetch(`${apiUrl}/api/health/decommission/refresh`, { method: "POST" });
            const data = await res.json();
            if (data.success) {
                toast.success(`Updated ${data.updated} indexes, ${data.escalated} auto-escalated`);
                fetchTracking();
            }
        } catch (e) {
            toast.error("Failed to refresh snapshots");
        }
    };

    const addToCart = (idx: IndexScore) => {
        const sql = `DROP INDEX IF EXISTS ${idx.schema_name}.${idx.index_name};`;
        if (!isInCart(sql)) {
            addItem({
                id: `drop-${idx.index_name}`,
                type: "drop",
                sql,
                description: `Drop unused index ${idx.index_name} on ${idx.table_name} (${idx.size_pretty}, score: ${idx.usefulness_score}/100)`,
                table: `${idx.schema_name}.${idx.table_name}`,
                estimatedImprovement: 0,
                source: "health",
            });
            toast.success(`Added DROP ${idx.index_name} to cart`);
        }
    };

    const getScoreColor = (score: number) => {
        if (score >= 70) return "text-green-500";
        if (score >= 40) return "text-yellow-500";
        if (score >= 10) return "text-orange-500";
        return "text-red-500";
    };

    const getScoreBg = (score: number) => {
        if (score >= 70) return "bg-green-500";
        if (score >= 40) return "bg-yellow-500";
        if (score >= 10) return "bg-orange-500";
        return "bg-red-500";
    };

    const getStageBadge = (stage: string) => {
        const styles: Record<string, string> = {
            active: "bg-green-500/10 text-green-500 border-green-500/20",
            monitoring: "bg-blue-500/10 text-blue-500 border-blue-500/20",
            ready_to_disable: "bg-orange-500/10 text-orange-500 border-orange-500/20",
            ready_to_drop: "bg-red-500/10 text-red-500 border-red-500/20",
            dropped: "bg-slate-500/10 text-slate-500 border-slate-500/20",
        };
        const labels: Record<string, string> = {
            active: "Active",
            monitoring: "Monitoring",
            ready_to_disable: "Ready to Disable",
            ready_to_drop: "Ready to Drop",
            dropped: "Dropped",
        };
        return (
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${styles[stage] || styles.active}`}>
                {labels[stage] || stage}
            </span>
        );
    };

    const getStageIcon = (stage: string) => {
        switch (stage) {
            case "active": return <CheckCircle2 className="w-4 h-4 text-green-500" />;
            case "monitoring": return <Eye className="w-4 h-4 text-blue-500" />;
            case "ready_to_disable": return <AlertTriangle className="w-4 h-4 text-orange-500" />;
            case "ready_to_drop": return <Trash2 className="w-4 h-4 text-red-500" />;
            default: return <Info className="w-4 h-4 text-slate-500" />;
        }
    };

    const isStructural = (idx: IndexScore) => idx.is_primary_key || idx.is_unique || idx.backs_constraint;
    const structuralCount = result?.indexes.filter(isStructural).length || 0;

    const filteredIndexes = result?.indexes.filter((idx) => {
        // Hide structural (PK/unique/FK) indexes unless toggled on
        if (!showStructural && isStructural(idx)) return false;

        if (filter === "all") return true;
        if (filter === "drop") return idx.recommended_stage === "ready_to_drop";
        if (filter === "disable") return idx.recommended_stage === "ready_to_disable";
        if (filter === "monitoring") return idx.recommended_stage === "monitoring";
        if (filter === "active") return idx.recommended_stage === "active";
        return true;
    }) || [];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className={`text-xl font-bold flex items-center gap-2 ${isDark ? "text-white" : "text-slate-900"}`}>
                        Unused Index Detection
                        <InfoTip isDark={isDark} text="Scores every index 0-100 based on scan frequency, write overhead, size, and constraint importance. Primary keys and unique indexes are always safe. Non-structural indexes below 40 are candidates for staged decommissioning." />
                    </h2>
                    <p className={`text-sm flex items-center gap-2 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                        Cost-benefit scoring with staged decommissioning
                        {cacheAge != null && (
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${
                                isDark ? "bg-slate-700 text-slate-400" : "bg-slate-100 text-slate-500"
                            }`}>
                                <Clock className="w-2.5 h-2.5" />
                                cached {cacheAge < 60 ? `${cacheAge}s` : cacheAge < 3600 ? `${Math.floor(cacheAge / 60)}m` : `${Math.floor(cacheAge / 3600)}h`} ago
                            </span>
                        )}
                    </p>
                </div>
            </div>

            {/* View Mode Toggle */}
            <div className={`p-1 rounded-lg flex gap-1 ${isDark ? "bg-slate-800" : "bg-slate-100"}`}>
                <button
                    onClick={() => setViewMode("analysis")}
                    className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all ${
                        viewMode === "analysis"
                            ? isDark ? "bg-slate-700 text-white shadow-sm" : "bg-white text-slate-800 shadow-sm"
                            : "text-slate-500 hover:text-slate-400"
                    }`}
                >
                    Index Analysis
                </button>
                <button
                    onClick={() => { setViewMode("tracking"); fetchTracking(); }}
                    className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all ${
                        viewMode === "tracking"
                            ? isDark ? "bg-slate-700 text-white shadow-sm" : "bg-white text-slate-800 shadow-sm"
                            : "text-slate-500 hover:text-slate-400"
                    }`}
                >
                    Decommission Tracker
                </button>
            </div>

            {/* ═══ ANALYSIS VIEW ═══ */}
            {viewMode === "analysis" && (
                <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                    {/* Run Analysis Button */}
                    {!result ? (
                        <button
                            onClick={() => runAnalysis(false)}
                            disabled={loading}
                            className={`w-full py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2 ${
                                loading
                                    ? "bg-blue-500/50 text-white cursor-not-allowed"
                                    : "bg-blue-600 hover:bg-blue-700 text-white"
                            }`}
                        >
                            {loading ? (
                                <><RefreshCw className="w-4 h-4 animate-spin" /> Scoring indexes...</>
                            ) : (
                                <><Database className="w-4 h-4" /> Analyze All Indexes</>
                            )}
                        </button>
                    ) : (
                        <button
                            onClick={() => runAnalysis(true)}
                            disabled={loading}
                            className={`w-full py-2 rounded-lg text-xs font-medium flex items-center justify-center gap-2 border ${
                                isDark
                                    ? "border-slate-600 text-slate-300 hover:bg-slate-700"
                                    : "border-slate-200 text-slate-600 hover:bg-slate-50"
                            }`}
                        >
                            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                            Fresh Scan
                        </button>
                    )}

                    {/* Stats Warning */}
                    {result && !result.stats_reliable && (
                        <div className={`p-3 rounded-lg text-xs flex items-start gap-2 ${
                            isDark ? "bg-yellow-900/20 text-yellow-300" : "bg-yellow-50 text-yellow-700"
                        }`}>
                            <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                            <span>
                                Statistics are only <strong>{result.stats_age_days} days</strong> old.
                                Scores may be unreliable. Wait for at least 7 days of data before making drop decisions.
                            </span>
                        </div>
                    )}

                    {/* Summary Cards */}
                    {result && (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            <div className={`p-3 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                                <div className="flex items-center gap-2 mb-1">
                                    <Trash2 className="w-3.5 h-3.5 text-red-500" />
                                    <span className={`text-[10px] font-bold uppercase tracking-wider ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                        Drop
                                    </span>
                                    <InfoTip isDark={isDark} text="Score 0-9. Index has zero scans, high write cost, and no constraint backing. Safe to drop after monitoring period." />
                                </div>
                                <div className="text-xl font-bold text-red-500">{result.summary.drop_candidates}</div>
                            </div>
                            <div className={`p-3 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                                <div className="flex items-center gap-2 mb-1">
                                    <AlertTriangle className="w-3.5 h-3.5 text-orange-500" />
                                    <span className={`text-[10px] font-bold uppercase tracking-wider ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                        Disable
                                    </span>
                                    <InfoTip isDark={isDark} text="Score 10-39. Very low usage relative to write overhead. Consider disabling and monitoring before dropping." />
                                </div>
                                <div className="text-xl font-bold text-orange-500">{result.summary.disable_candidates}</div>
                            </div>
                            <div className={`p-3 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                                <div className="flex items-center gap-2 mb-1">
                                    <Eye className="w-3.5 h-3.5 text-blue-500" />
                                    <span className={`text-[10px] font-bold uppercase tracking-wider ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                        Monitor
                                    </span>
                                    <InfoTip isDark={isDark} text="Score 40-69. Low but non-zero usage. Watch for 14+ days before deciding — may be used by batch jobs or reporting queries." />
                                </div>
                                <div className="text-xl font-bold text-blue-500">{result.summary.monitoring}</div>
                            </div>
                            <div className={`p-3 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                                <div className="flex items-center gap-2 mb-1">
                                    <HardDrive className="w-3.5 h-3.5 text-yellow-500" />
                                    <span className={`text-[10px] font-bold uppercase tracking-wider ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                        Reclaimable
                                    </span>
                                    <InfoTip isDark={isDark} text="Total disk space used by indexes in Drop + Disable categories. This space is freed when you drop these indexes." />
                                </div>
                                <div className="text-xl font-bold text-yellow-500">{result.summary.total_reclaimable_pretty}</div>
                            </div>
                        </div>
                    )}

                    {/* Filter Pills */}
                    {result && result.indexes.length > 0 && (
                        <div className="flex items-center gap-2 flex-wrap">
                            {(["all", "drop", "disable", "monitoring", "active"] as const).map((f) => {
                                // Counts exclude structural indexes in non-active filters
                                const nonStructural = result.indexes.filter((i) => !isStructural(i));
                                const counts: Record<string, number> = {
                                    all: showStructural ? result.total_indexes : nonStructural.length,
                                    drop: result.summary.drop_candidates,
                                    disable: result.summary.disable_candidates,
                                    monitoring: result.summary.monitoring,
                                    active: showStructural ? result.summary.healthy : result.summary.healthy - structuralCount,
                                };
                                return (
                                    <button
                                        key={f}
                                        onClick={() => setFilter(f)}
                                        className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                                            filter === f
                                                ? "bg-blue-600 text-white"
                                                : isDark
                                                    ? "bg-slate-800 text-slate-400 hover:bg-slate-700"
                                                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                                        }`}
                                    >
                                        {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)} ({counts[f]})
                                    </button>
                                );
                            })}

                            {/* Structural toggle */}
                            <div className="ml-auto flex items-center gap-2">
                                <button
                                    onClick={() => setShowStructural(!showStructural)}
                                    className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-all ${
                                        showStructural
                                            ? "bg-purple-600 text-white"
                                            : isDark
                                                ? "bg-slate-800 text-slate-500 hover:bg-slate-700"
                                                : "bg-slate-100 text-slate-400 hover:bg-slate-200"
                                    }`}
                                >
                                    <ShieldCheck className="w-3 h-3" />
                                    {showStructural ? "Hide" : "Show"} PKs & Constraints ({structuralCount})
                                </button>
                                <InfoTip isDark={isDark} text="Primary keys, unique constraints, and FK-backing indexes always show 0 scans because Postgres uses them internally for constraint enforcement, which isn't tracked by idx_scan. They're hidden by default since they can never be dropped." />
                            </div>
                        </div>
                    )}

                    {/* Batch Actions */}
                    {result && (result.summary.drop_candidates > 0 || result.summary.disable_candidates > 0) && (
                        <div className="flex gap-2">
                            <button
                                onClick={() => {
                                    const candidates = result.indexes.filter(
                                        (i) => i.recommended_stage === "ready_to_drop" || i.recommended_stage === "ready_to_disable"
                                    );
                                    startMonitoring(candidates);
                                }}
                                className={`flex-1 py-2 rounded-lg text-xs font-medium border flex items-center justify-center gap-2 ${
                                    isDark
                                        ? "border-blue-700 text-blue-400 hover:bg-blue-900/20"
                                        : "border-blue-200 text-blue-600 hover:bg-blue-50"
                                }`}
                            >
                                <Eye className="w-3.5 h-3.5" />
                                Start Monitoring All Candidates ({result.summary.drop_candidates + result.summary.disable_candidates})
                            </button>
                        </div>
                    )}

                    {/* Index List */}
                    {filteredIndexes.length > 0 && (
                        <div className={`rounded-xl border overflow-hidden ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                            <div className="divide-y divide-slate-700/50">
                                {filteredIndexes.map((idx) => {
                                    const isExpanded = expandedIndex === idx.index_name;
                                    const dropSql = `DROP INDEX IF EXISTS ${idx.schema_name}.${idx.index_name};`;
                                    const inCart = isInCart(dropSql);

                                    return (
                                        <div key={idx.index_name} className="p-3">
                                            {/* Row Header */}
                                            <div
                                                className="flex items-center gap-3 cursor-pointer"
                                                onClick={() => setExpandedIndex(isExpanded ? null : idx.index_name)}
                                            >
                                                {/* Score Circle */}
                                                <div className="relative w-10 h-10 flex-shrink-0">
                                                    <svg className="w-10 h-10 -rotate-90" viewBox="0 0 36 36">
                                                        <circle cx="18" cy="18" r="15.5" fill="none" strokeWidth="3"
                                                            className={isDark ? "stroke-slate-700" : "stroke-slate-200"} />
                                                        <circle cx="18" cy="18" r="15.5" fill="none" strokeWidth="3"
                                                            strokeDasharray={`${idx.usefulness_score} ${100 - idx.usefulness_score}`}
                                                            strokeLinecap="round"
                                                            className={getScoreBg(idx.usefulness_score).replace("bg-", "stroke-")} />
                                                    </svg>
                                                    <span className={`absolute inset-0 flex items-center justify-center text-[10px] font-bold ${getScoreColor(idx.usefulness_score)}`}>
                                                        {Math.round(idx.usefulness_score)}
                                                    </span>
                                                </div>

                                                {/* Index Info */}
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2">
                                                        <span className={`text-sm font-medium truncate ${isDark ? "text-white" : "text-slate-900"}`}>
                                                            {idx.index_name}
                                                        </span>
                                                        {idx.constraint_type && (
                                                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-purple-500/10 text-purple-500 border border-purple-500/20">
                                                                {idx.constraint_type}
                                                            </span>
                                                        )}
                                                        {getStageBadge(idx.recommended_stage)}
                                                    </div>
                                                    <div className={`text-xs mt-0.5 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                                        {idx.schema_name}.{idx.table_name} &middot; {idx.size_pretty} &middot; {idx.scan_rate_per_day} scans/day
                                                    </div>
                                                </div>

                                                {/* Quick Actions */}
                                                <div className="flex items-center gap-1.5 flex-shrink-0">
                                                    {idx.recommended_stage !== "active" && !idx.is_primary_key && (
                                                        <button
                                                            onClick={(e) => { e.stopPropagation(); addToCart(idx); }}
                                                            disabled={inCart}
                                                            className={`p-1.5 rounded-md text-xs ${
                                                                inCart
                                                                    ? "bg-green-500/10 text-green-500"
                                                                    : isDark
                                                                        ? "bg-slate-700 text-slate-300 hover:bg-slate-600"
                                                                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                                                            }`}
                                                            title={inCart ? "In cart" : "Add DROP to cart"}
                                                        >
                                                            {inCart ? <Check className="w-3.5 h-3.5" /> : <ShoppingCart className="w-3.5 h-3.5" />}
                                                        </button>
                                                    )}
                                                    {isExpanded ? (
                                                        <ChevronUp className="w-4 h-4 text-slate-400" />
                                                    ) : (
                                                        <ChevronDown className="w-4 h-4 text-slate-400" />
                                                    )}
                                                </div>
                                            </div>

                                            {/* Expanded Details */}
                                            {isExpanded && (
                                                <div className="mt-3 ml-[52px] space-y-3">
                                                    {/* Score Breakdown */}
                                                    <div className={`p-3 rounded-lg ${isDark ? "bg-slate-900/50" : "bg-slate-50"}`}>
                                                        <p className={`text-[10px] font-bold uppercase tracking-wider mb-2 flex items-center gap-1.5 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                                            Score Breakdown
                                                            <InfoTip isDark={isDark} text="Usefulness score (0-100) = Scan Rate + Cost-Benefit + Size + Constraint. Higher = more useful. Indexes scoring 70+ are healthy, 40-69 need monitoring, below 40 are candidates for removal." />
                                                        </p>
                                                        <div className="grid grid-cols-4 gap-2 text-xs">
                                                            <div>
                                                                <div className={`flex items-center gap-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                                                    Scan Rate
                                                                    <InfoTip isDark={isDark} text="How often this index is used for queries (0-40 pts). Based on idx_scan / days since stats reset. Logarithmic scale: 1 scan/day = 20pts, 10/day = 30pts, 100/day = 40pts. Note: PKs show 0 scans because constraint enforcement doesn't count as a scan." />
                                                                </div>
                                                                <div className={`font-bold ${isDark ? "text-white" : "text-slate-800"}`}>
                                                                    {idx.score_breakdown.scan_score}/40
                                                                </div>
                                                            </div>
                                                            <div>
                                                                <div className={`flex items-center gap-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                                                    Cost-Benefit
                                                                    <InfoTip isDark={isDark} text="Is this index earning its keep? (0-30 pts). Compares index scans vs table writes (INSERT+UPDATE+DELETE). An index with 0 scans on a write-heavy table = pure overhead. On a read-only table = free to keep." />
                                                                </div>
                                                                <div className={`font-bold ${isDark ? "text-white" : "text-slate-800"}`}>
                                                                    {idx.score_breakdown.cost_score}/30
                                                                </div>
                                                            </div>
                                                            <div>
                                                                <div className={`flex items-center gap-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                                                    Size
                                                                    <InfoTip isDark={isDark} text="Penalty based on index size (0-10 pts). Smaller unused indexes are less harmful (less cache pollution, less write overhead). <1MB = 10pts, 10MB = 8pts, 100MB = 5pts, >1GB = 0pts." />
                                                                </div>
                                                                <div className={`font-bold ${isDark ? "text-white" : "text-slate-800"}`}>
                                                                    {idx.score_breakdown.size_score}/10
                                                                </div>
                                                            </div>
                                                            <div>
                                                                <div className={`flex items-center gap-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                                                    Constraint
                                                                    <InfoTip isDark={isDark} text="Bonus for structural indexes (+20 pts). Primary keys, unique constraints, and FK-backing indexes are required for data integrity — they should never be dropped even with 0 scans. These indexes are always locked to 'Active' status." />
                                                                </div>
                                                                <div className={`font-bold ${idx.score_breakdown.constraint_bonus > 0 ? "text-purple-500" : isDark ? "text-white" : "text-slate-800"}`}>
                                                                    +{idx.score_breakdown.constraint_bonus}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Metrics */}
                                                    <div className={`p-3 rounded-lg ${isDark ? "bg-slate-900/50" : "bg-slate-50"}`}>
                                                        <p className={`text-[10px] font-bold uppercase tracking-wider mb-2 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                                            Raw Metrics
                                                        </p>
                                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                                                            <div>
                                                                <div className={`flex items-center gap-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                                                    Total Scans
                                                                    <InfoTip isDark={isDark} text="pg_stat_user_indexes.idx_scan — counts explicit Index Scan / Index Only Scan plan nodes. Does NOT count constraint enforcement (PK uniqueness checks, FK lookups), so 0 is normal for primary keys." />
                                                                </div>
                                                                <div className={`font-mono ${isDark ? "text-white" : "text-slate-800"}`}>
                                                                    {idx.idx_scan.toLocaleString()}
                                                                </div>
                                                            </div>
                                                            <div>
                                                                <div className={`flex items-center gap-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                                                    Table Writes
                                                                    <InfoTip isDark={isDark} text="Total INSERT + UPDATE + DELETE on this table since stats reset. Every write must update every index on the table — more indexes = slower writes." />
                                                                </div>
                                                                <div className={`font-mono ${isDark ? "text-white" : "text-slate-800"}`}>
                                                                    {idx.total_writes.toLocaleString()}
                                                                </div>
                                                            </div>
                                                            <div>
                                                                <div className={`flex items-center gap-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                                                    Read/Write Ratio
                                                                    <InfoTip isDark={isDark} text="idx_scan / total_writes. Values >1 mean the index is read more than written (good). Values near 0 mean the index costs writes but rarely helps reads (bad). -1 means no writes (index is free)." />
                                                                </div>
                                                                <div className={`font-mono ${isDark ? "text-white" : "text-slate-800"}`}>
                                                                    {idx.write_overhead_ratio === -1 ? "No writes" : idx.write_overhead_ratio.toFixed(4)}
                                                                </div>
                                                            </div>
                                                            <div>
                                                                <div className={isDark ? "text-slate-500" : "text-slate-400"}>Index Size</div>
                                                                <div className={`font-mono ${isDark ? "text-white" : "text-slate-800"}`}>
                                                                    {idx.size_pretty}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {idx.confidence_note && (
                                                        <div className={`p-2 rounded-lg text-xs flex items-start gap-2 ${
                                                            isDark ? "bg-yellow-900/20 text-yellow-300" : "bg-yellow-50 text-yellow-700"
                                                        }`}>
                                                            <Clock className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                                                            {idx.confidence_note}
                                                        </div>
                                                    )}

                                                    {/* Actions */}
                                                    {idx.recommended_stage !== "active" && !idx.is_primary_key && (
                                                        <div className="flex gap-2">
                                                            <button
                                                                onClick={() => startMonitoring([idx])}
                                                                className={`flex-1 py-1.5 rounded-lg text-xs font-medium border flex items-center justify-center gap-1.5 ${
                                                                    isDark
                                                                        ? "border-blue-700 text-blue-400 hover:bg-blue-900/20"
                                                                        : "border-blue-200 text-blue-600 hover:bg-blue-50"
                                                                }`}
                                                            >
                                                                <Eye className="w-3.5 h-3.5" /> Start Monitoring
                                                            </button>
                                                            <button
                                                                onClick={() => addToCart(idx)}
                                                                disabled={inCart}
                                                                className={`flex-1 py-1.5 rounded-lg text-xs font-medium border flex items-center justify-center gap-1.5 ${
                                                                    inCart
                                                                        ? "border-green-700 text-green-400"
                                                                        : isDark
                                                                            ? "border-red-700 text-red-400 hover:bg-red-900/20"
                                                                            : "border-red-200 text-red-600 hover:bg-red-50"
                                                                }`}
                                                            >
                                                                {inCart ? <><Check className="w-3.5 h-3.5" /> In Cart</> : <><Trash2 className="w-3.5 h-3.5" /> Add DROP to Cart</>}
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Empty State */}
                    {!result && !loading && (
                        <div className={`p-12 text-center rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                            <TrendingDown className={`w-12 h-12 mx-auto mb-4 ${isDark ? "text-slate-600" : "text-slate-300"}`} />
                            <h3 className={`text-lg font-medium mb-1 ${isDark ? "text-slate-200" : "text-slate-800"}`}>
                                Index Intelligence
                            </h3>
                            <p className={`mb-1 text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                Score every index by cost-benefit ratio, scan rate, and write overhead.
                            </p>
                            <p className={`text-xs ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                Identifies drop candidates, flags seasonal indexes, and prevents unsafe drops.
                            </p>
                        </div>
                    )}
                </div>
            )}

            {/* ═══ DECOMMISSION TRACKER VIEW ═══ */}
            {viewMode === "tracking" && (
                <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                    {/* Refresh Button */}
                    <div className="flex gap-2">
                        <button
                            onClick={fetchTracking}
                            disabled={loadingTracking}
                            className={`flex-1 py-2 rounded-lg text-sm font-medium border flex items-center justify-center gap-2 ${
                                isDark
                                    ? "border-slate-600 text-slate-300 hover:bg-slate-700"
                                    : "border-slate-200 text-slate-600 hover:bg-slate-50"
                            }`}
                        >
                            <RefreshCw className={`w-4 h-4 ${loadingTracking ? "animate-spin" : ""}`} /> Refresh
                        </button>
                        <button
                            onClick={refreshSnapshots}
                            className={`flex-1 py-2 rounded-lg text-sm font-medium border flex items-center justify-center gap-2 ${
                                isDark
                                    ? "border-blue-700 text-blue-400 hover:bg-blue-900/20"
                                    : "border-blue-200 text-blue-600 hover:bg-blue-50"
                            }`}
                        >
                            <Database className="w-4 h-4" /> Take Snapshot
                        </button>
                    </div>

                    {/* Workflow Explainer */}
                    <div className={`p-3 rounded-lg text-xs space-y-2 ${isDark ? "bg-blue-900/20 text-blue-300" : "bg-blue-50 text-blue-700"}`}>
                        <div>
                            <strong>How decommissioning works:</strong>
                        </div>
                        <div className="flex items-center gap-1 flex-wrap">
                            <span className="px-1.5 py-0.5 rounded bg-blue-500/20 font-bold">Monitoring</span>
                            <ArrowRight className="w-3 h-3" />
                            <span className="px-1.5 py-0.5 rounded bg-orange-500/20 font-bold">Ready to Disable</span>
                            <ArrowRight className="w-3 h-3" />
                            <span className="px-1.5 py-0.5 rounded bg-red-500/20 font-bold">Ready to Drop</span>
                            <ArrowRight className="w-3 h-3" />
                            <span className="px-1.5 py-0.5 rounded bg-slate-500/20 font-bold">Dropped</span>
                        </div>
                        <div className={isDark ? "text-blue-400/70" : "text-blue-600/70"}>
                            Auto-escalation: after 14 days with 0 new scans, indexes move to the next stage.
                            If an index gains 10+ scans during monitoring, it de-escalates back to Active (false alarm).
                            Take snapshots regularly to track scan trends.
                        </div>
                    </div>

                    {/* Tracked Indexes */}
                    {tracking.length > 0 ? (
                        <div className={`rounded-xl border overflow-hidden ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                            <div className="divide-y divide-slate-700/50">
                                {tracking.map((entry) => (
                                    <div key={entry.id} className="p-3">
                                        <div className="flex items-center gap-3">
                                            {getStageIcon(entry.stage)}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <span className={`text-sm font-medium truncate ${isDark ? "text-white" : "text-slate-900"}`}>
                                                        {entry.index_name}
                                                    </span>
                                                    {getStageBadge(entry.stage)}
                                                </div>
                                                <div className={`text-xs mt-0.5 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                                    {entry.schema_name}.{entry.table_name} &middot;
                                                    Score: {entry.usefulness_score} &middot;
                                                    Scans at start: {entry.idx_scan_at_start}
                                                    {entry.notes && ` &middot; ${entry.notes}`}
                                                </div>
                                            </div>

                                            {/* Stage progression buttons */}
                                            <div className="flex items-center gap-1.5 flex-shrink-0">
                                                {entry.stage === "monitoring" && (
                                                    <button
                                                        onClick={() => updateStage(entry.id, "ready_to_disable", "Manually escalated")}
                                                        className={`px-2 py-1 rounded text-[10px] font-bold ${
                                                            isDark
                                                                ? "bg-orange-900/20 text-orange-400 hover:bg-orange-900/40"
                                                                : "bg-orange-50 text-orange-600 hover:bg-orange-100"
                                                        }`}
                                                    >
                                                        Escalate
                                                    </button>
                                                )}
                                                {entry.stage === "ready_to_disable" && (
                                                    <button
                                                        onClick={() => updateStage(entry.id, "ready_to_drop", "Confirmed safe to drop")}
                                                        className={`px-2 py-1 rounded text-[10px] font-bold ${
                                                            isDark
                                                                ? "bg-red-900/20 text-red-400 hover:bg-red-900/40"
                                                                : "bg-red-50 text-red-600 hover:bg-red-100"
                                                        }`}
                                                    >
                                                        Ready to Drop
                                                    </button>
                                                )}
                                                {entry.stage === "ready_to_drop" && (
                                                    <button
                                                        onClick={() => {
                                                            const sql = `DROP INDEX IF EXISTS ${entry.schema_name}.${entry.index_name};`;
                                                            if (!isInCart(sql)) {
                                                                addItem({
                                                                    id: `drop-${entry.index_name}`,
                                                                    type: "drop",
                                                                    sql,
                                                                    description: `Drop decommissioned index ${entry.index_name}`,
                                                                    table: `${entry.schema_name}.${entry.table_name}`,
                                                                    estimatedImprovement: 0,
                                                                    source: "health",
                                                                });
                                                                toast.success("Added to cart");
                                                            }
                                                        }}
                                                        className={`px-2 py-1 rounded text-[10px] font-bold ${
                                                            isDark
                                                                ? "bg-red-900/20 text-red-400 hover:bg-red-900/40"
                                                                : "bg-red-50 text-red-600 hover:bg-red-100"
                                                        }`}
                                                    >
                                                        <ShoppingCart className="w-3 h-3 inline mr-1" />
                                                        Add DROP to Cart
                                                    </button>
                                                )}
                                                {/* De-escalate back to active */}
                                                {entry.stage !== "active" && entry.stage !== "dropped" && (
                                                    <button
                                                        onClick={() => updateStage(entry.id, "active", "Manually marked as active")}
                                                        className={`px-2 py-1 rounded text-[10px] font-bold ${
                                                            isDark
                                                                ? "bg-green-900/20 text-green-400 hover:bg-green-900/40"
                                                                : "bg-green-50 text-green-600 hover:bg-green-100"
                                                        }`}
                                                    >
                                                        Keep
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className={`p-12 text-center rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                            <Eye className={`w-12 h-12 mx-auto mb-4 ${isDark ? "text-slate-600" : "text-slate-300"}`} />
                            <h3 className={`text-lg font-medium mb-1 ${isDark ? "text-slate-200" : "text-slate-800"}`}>
                                No Indexes Being Tracked
                            </h3>
                            <p className={isDark ? "text-slate-400" : "text-slate-500"}>
                                Run an analysis first, then start monitoring candidates.
                            </p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
