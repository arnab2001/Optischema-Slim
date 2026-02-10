import { useState } from "react";
import { useAppStore } from "@/store/appStore";
import {
    AlertTriangle,
    Database,
    Settings,
    Activity,
    ArrowRight,
    Eye,
    Play,
    ChevronDown,
    ChevronUp,
    Clipboard,
    Check,
    ArrowUpRight,
    Terminal,
    Info
} from "lucide-react";
import { toast } from "sonner";

interface Issue {
    type: "QUERY" | "CONFIG" | "SCHEMA" | "SYSTEM";
    severity: "CRITICAL" | "WARNING" | "INFO";
    title: string;
    description: string;
    action_payload: string;
}

interface IssueCardProps {
    issue: Issue;
    extraData?: any;
    onAction: (issue: Issue) => void;
}

export function IssueCard({ issue, extraData, onAction }: IssueCardProps) {
    const { theme } = useAppStore();
    const isDark = theme === "dark";
    const [isExpanded, setIsExpanded] = useState(false);
    const [showFullSql, setShowFullSql] = useState(false);
    const [copied, setCopied] = useState(false);

    const formatBytes = (bytes: number) => {
        if (bytes === 0) return "0 B";
        const k = 1024;
        const dm = bytes < k * 100 ? 2 : 1;
        const sizes = ["B", "KB", "MB", "GB", "TB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
    };

    const handleCopy = (text: string, label: string) => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        toast.success(`${label} copied to clipboard`);
        setTimeout(() => setCopied(false), 2000);
    };

    // Icon & Color mapping
    const getIcon = () => {
        switch (issue.type) {
            case "QUERY": return Activity;
            case "CONFIG": return Settings;
            case "SCHEMA": return Database;
            default: return AlertTriangle;
        }
    };

    const getStatusColor = () => {
        switch (issue.severity) {
            case "CRITICAL": return "text-red-500";
            case "WARNING": return "text-yellow-500";
            case "INFO": return "text-blue-500";
            default: return "text-slate-500";
        }
    };

    const getStatusBg = () => {
        switch (issue.severity) {
            case "CRITICAL": return "bg-red-500/10";
            case "WARNING": return "bg-yellow-500/10";
            case "INFO": return "bg-blue-500/10";
            default: return "bg-slate-500/10";
        }
    };

    const Icon = getIcon();
    const statusColor = getStatusColor();
    const statusBg = getStatusBg();

    const renderTitle = () => {
        const parts = issue.title.split("'");
        if (parts.length >= 3) {
            return (
                <>
                    {parts[0]}
                    <span className="font-mono bg-black/5 dark:bg-white/5 px-1.5 py-0.5 rounded text-blue-400">
                        {parts[1]}
                    </span>
                    {parts.slice(2).join("'")}
                </>
            );
        }
        return issue.title;
    };

    return (
        <div className={`group rounded-xl border transition-all duration-200 overflow-hidden ${isDark
            ? "bg-slate-800/20 border-slate-700/50 hover:border-slate-600"
            : "bg-white border-slate-200 hover:border-slate-300 hover:shadow-sm"
            }`}>
            <div className="flex items-center gap-3 p-3 transition-colors hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
                {/* Icon Box */}
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${statusBg} ${statusColor}`}>
                    <Icon className="w-4.5 h-4.5" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                        <h4 className={`text-sm font-bold truncate ${isDark ? "text-slate-200" : "text-slate-800"}`}>
                            {renderTitle()}
                        </h4>
                        {issue.severity === "CRITICAL" && (
                            <span className="text-[9px] font-black bg-red-500 text-white px-1.5 py-0.5 rounded-sm tracking-tighter shadow-sm shadow-red-500/20">CRITICAL</span>
                        )}
                    </div>
                    <p className={`text-[11px] truncate ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                        {issue.description}
                    </p>
                </div>

                {/* Expansion Toggle */}
                <div className="flex items-center">
                    <div className={`p-1.5 rounded-lg transition-colors ${isDark ? "text-slate-500 group-hover:text-slate-300" : "text-slate-400 group-hover:text-slate-600"}`}>
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </div>
                </div>
            </div>

            {/* Expanded Content */}
            {isExpanded && (
                <div className={`${isDark ? "bg-slate-950/60" : "bg-slate-50/80"} border-t ${isDark ? "border-slate-800" : "border-slate-200"} animate-in slide-in-from-top-2 duration-200`}>
                    <div className="p-4 space-y-4">

                        {/* 1. High Impact Query */}
                        {issue.type === "QUERY" && extraData && (
                            <>
                                {/* Top Row: Evidence */}
                                <div className="grid grid-cols-3 gap-4">
                                    <div className={`${isDark ? "bg-black/40" : "bg-white"} p-2 rounded border ${isDark ? "border-white/5" : "border-slate-200"}`}>
                                        <span className={`text-[10px] uppercase font-bold tracking-wider block mb-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>Call Count</span>
                                        <span className={`text-sm font-mono font-bold tabular-nums ${isDark ? "text-slate-300" : "text-slate-700"}`}>
                                            {extraData.calls?.toLocaleString()}
                                            <span className="text-[10px] ml-1.5 font-normal text-slate-500">{extraData.calls > 1000 ? "(Spam?)" : ""}</span>
                                        </span>
                                    </div>
                                    <div className={`${isDark ? "bg-black/40" : "bg-white"} p-2 rounded border ${isDark ? "border-white/5" : "border-slate-200"}`}>
                                        <span className={`text-[10px] uppercase font-bold tracking-wider block mb-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>Mean Time</span>
                                        <span className={`text-sm font-mono font-bold tabular-nums ${extraData.mean_exec_time > 100 ? "text-red-400" : isDark ? "text-slate-300" : "text-slate-700"}`}>
                                            {extraData.mean_exec_time?.toFixed(1)}ms
                                            {extraData.mean_exec_time > 100 ? <span className="text-[10px] ml-1.5 font-normal text-slate-500">(Slow)</span> : ""}
                                        </span>
                                    </div>
                                    <div className={`${isDark ? "bg-black/40" : "bg-white"} p-2 rounded border ${isDark ? "border-white/5" : "border-slate-200"}`}>
                                        <span className={`text-[10px] uppercase font-bold tracking-wider block mb-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>Rows</span>
                                        <span className={`text-sm font-mono font-bold tabular-nums ${isDark ? "text-slate-300" : "text-slate-700"}`}>
                                            {extraData.rows?.toLocaleString()}
                                            <span className="text-[10px] ml-1.5 font-normal text-slate-500">{extraData.rows > 1000 ? "(Bulk?)" : ""}</span>
                                        </span>
                                    </div>
                                </div>

                                {/* Middle Row: The Code */}
                                <div className="space-y-1.5">
                                    <div className="flex items-center justify-between">
                                        <span className={`text-[10px] uppercase font-bold tracking-widest ${isDark ? "text-slate-500" : "text-slate-400"}`}>SQL Snippet</span>
                                        <button
                                            onClick={() => setShowFullSql(!showFullSql)}
                                            className="text-[10px] text-blue-500 hover:underline font-bold"
                                        >
                                            {showFullSql ? "Show Less" : "Show Full"}
                                        </button>
                                    </div>
                                    <div className="relative group/code">
                                        <pre className={`font-mono text-[11px] bg-black p-3 rounded-lg border transition-all duration-300 overflow-x-auto whitespace-pre-wrap ${isDark ? "text-slate-300 border-slate-800" : "text-slate-400 border-slate-700"} ${showFullSql ? "max-h-[300px]" : "max-h-24"}`}>
                                            {extraData.query}
                                        </pre>
                                        <button
                                            onClick={() => handleCopy(extraData.query, "SQL")}
                                            className="absolute top-2 right-2 p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded opacity-0 group-hover/code:opacity-100 transition-opacity"
                                        >
                                            <Clipboard className="w-3 h-3" />
                                        </button>
                                    </div>
                                </div>

                                {/* Bottom Row: Actions */}
                                <div className="flex items-center gap-3 mt-4">
                                    <button
                                        onClick={() => onAction(issue)}
                                        className="flex-1 flex items-center justify-center gap-2 py-2 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold transition-all shadow-lg shadow-blue-500/20"
                                    >
                                        <Activity className="w-3.5 h-3.5" />
                                        Analyze Plan
                                        <ArrowUpRight className="w-3 h-3" />
                                    </button>
                                    <button
                                        onClick={() => handleCopy(issue.action_payload, "Query ID")}
                                        className={`py-2 px-4 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${isDark ? "bg-slate-800 hover:bg-slate-700 text-slate-300" : "bg-slate-200 hover:bg-slate-300 text-slate-700"}`}
                                    >
                                        <Terminal className="w-3.5 h-3.5" />
                                        Copy QID
                                    </button>
                                </div>
                            </>
                        )}

                        {/* 2. Table Bloat */}
                        {issue.type === "SCHEMA" && issue.title.toLowerCase().includes("bloat") && extraData && (
                            <>
                                {Array.isArray(extraData) ? (
                                    <div className="space-y-3">
                                        <span className={`text-[10px] uppercase font-bold tracking-widest ${isDark ? "text-slate-500" : "text-slate-400"}`}>Tables with High Bloat</span>
                                        <div className={`rounded-lg border overflow-hidden ${isDark ? "border-slate-800" : "border-slate-200"}`}>
                                            <table className="w-full text-[11px] font-mono">
                                                <thead className={`${isDark ? "bg-black/40 text-slate-500" : "bg-slate-100 text-slate-500"} border-b ${isDark ? "border-slate-800" : "border-slate-200"}`}>
                                                    <tr>
                                                        <th className="px-3 py-2 text-left font-bold">Table</th>
                                                        <th className="px-3 py-2 text-right font-bold">Dead Ratio</th>
                                                        <th className="px-3 py-2 text-right font-bold">Wasted</th>
                                                    </tr>
                                                </thead>
                                                <tbody className={`divide-y ${isDark ? "divide-slate-800" : "divide-slate-200"}`}>
                                                    {extraData.map((b, idx) => (
                                                        <tr key={idx} className={`${isDark ? "bg-black/20 hover:bg-black/40" : "bg-white hover:bg-slate-50"} transition-colors`}>
                                                            <td className={`px-3 py-2 font-bold ${isDark ? "text-blue-400" : "text-blue-600"}`}>{b.table}</td>
                                                            <td className={`px-3 py-2 text-right font-bold ${b.dead_ratio > 30 ? "text-red-500" : isDark ? "text-slate-300" : "text-slate-700"}`}>{b.dead_ratio}%</td>
                                                            <td className={`px-3 py-2 text-right ${isDark ? "text-slate-400" : "text-slate-500"}`}>{formatBytes(b.total_bytes * (b.dead_ratio / 100))}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                ) : (
                                    <>
                                        {/* Single Table View (existing) */}
                                        <div className="space-y-2">
                                            <div className={`flex items-center justify-between text-[10px] font-bold uppercase tracking-wider ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                                <span>Tuples Distribution</span>
                                                <div className="flex gap-3">
                                                    <div className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Live</div>
                                                    <div className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-red-500" /> Dead (Bloat)</div>
                                                </div>
                                            </div>
                                            <div className={`w-full h-2.5 rounded-full overflow-hidden flex ring-1 ${isDark ? "bg-slate-800/50 ring-white/5" : "bg-slate-200 ring-black/5"}`}>
                                                <div style={{ width: `${100 - extraData.dead_ratio}%` }} className="bg-emerald-500/60 transition-all duration-1000" />
                                                <div style={{ width: `${extraData.dead_ratio}%` }} className="bg-red-500/60 transition-all duration-1000" />
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-3 gap-4 text-[11px] font-mono">
                                            <div className={`${isDark ? "bg-black/20" : "bg-white border-slate-200"} p-2.5 rounded border ${isDark ? "border-white/5" : ""}`}>
                                                <span className={`${isDark ? "text-slate-500" : "text-slate-400"} block text-[9px] uppercase font-bold tracking-wider mb-1`}>Wasted Space</span>
                                                <span className="text-red-400 font-bold text-sm">
                                                    {extraData.total_bytes ? formatBytes(extraData.total_bytes * (extraData.dead_ratio / 100)) : "Checking..."}
                                                </span>
                                            </div>
                                            <div className={`${isDark ? "bg-black/20" : "bg-white border-slate-200"} p-2.5 rounded border ${isDark ? "border-white/5" : ""}`}>
                                                <span className={`${isDark ? "text-slate-500" : "text-slate-400"} block text-[9px] uppercase font-bold tracking-wider mb-1`}>Dead Tuples</span>
                                                <span className={`${isDark ? "text-slate-300" : "text-slate-700"} font-bold text-sm`}>{extraData.dead_tuples?.toLocaleString()} <span className="text-[10px] opacity-50 font-normal">({extraData.dead_ratio}%)</span></span>
                                            </div>
                                            <div className={`${isDark ? "bg-black/20" : "bg-white border-slate-200"} p-2.5 rounded border ${isDark ? "border-white/5" : ""}`}>
                                                <span className={`${isDark ? "text-slate-500" : "text-slate-400"} block text-[9px] uppercase font-bold tracking-wider mb-1`}>Last Vacuum</span>
                                                <span className="text-orange-400 font-bold text-sm">{extraData.last_autovacuum ? "3 days ago" : "Never"}</span>
                                            </div>
                                        </div>

                                        <div className="space-y-1.5">
                                            <span className={`text-[10px] uppercase font-bold tracking-widest ${isDark ? "text-slate-500" : "text-slate-400"}`}>Recommended Fix</span>
                                            <div className={`flex items-center gap-3 rounded-lg p-2.5 border group/fix ${isDark ? "bg-black/40 border-slate-800" : "bg-white border-slate-200"}`}>
                                                <code className={`text-[11px] font-mono flex-1 truncate ${isDark ? "text-blue-400" : "text-blue-600"}`}>
                                                    {extraData.recommendation}
                                                </code>
                                                <button
                                                    onClick={() => handleCopy(extraData.recommendation, "Fix SQL")}
                                                    className={`h-7 w-7 flex items-center justify-center rounded transition-colors ${isDark ? "bg-slate-800 hover:bg-slate-700 text-slate-400" : "bg-slate-100 hover:bg-slate-200 text-slate-500"}`}
                                                >
                                                    <Clipboard className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        </div>
                                    </>
                                )}
                            </>
                        )}

                        {/* 3. Unused Indexes */}
                        {issue.type === "SCHEMA" && issue.title.toLowerCase().includes("index") && extraData && (
                            <div className="space-y-3">
                                <span className={`text-[10px] uppercase font-bold tracking-widest ${isDark ? "text-slate-500" : "text-slate-400"}`}>Unused Index Candidates</span>
                                <div className={`rounded-lg border overflow-hidden ${isDark ? "border-slate-800" : "border-slate-200"}`}>
                                    <table className="w-full text-[11px] font-mono">
                                        <thead className={`${isDark ? "bg-black/40 text-slate-500" : "bg-slate-100 text-slate-500"} border-b ${isDark ? "border-slate-800" : "border-slate-200"}`}>
                                            <tr>
                                                <th className="px-3 py-2 text-left font-bold">Index Name</th>
                                                <th className="px-3 py-2 text-right font-bold">Size</th>
                                                <th className="px-3 py-2 text-right font-bold">Scans</th>
                                                <th className="px-3 py-2 w-10"></th>
                                            </tr>
                                        </thead>
                                        <tbody className={`divide-y ${isDark ? "divide-slate-800" : "divide-slate-200"}`}>
                                            {(Array.isArray(extraData) ? extraData : [extraData]).map((idxObj, idx) => (
                                                <tr key={idx} className={`${isDark ? "bg-black/20 hover:bg-black/40" : "bg-white hover:bg-slate-50"} transition-colors`}>
                                                    <td className={`px-3 py-2 font-bold truncate max-w-[140px] ${isDark ? "text-blue-400" : "text-blue-600"}`}>{idxObj.index}</td>
                                                    <td className={`px-3 py-2 text-right ${isDark ? "text-slate-300" : "text-slate-700"}`}>{idxObj.size}</td>
                                                    <td className={`px-3 py-2 text-right font-bold ${isDark ? "text-red-500" : "text-red-600"}`}>{idxObj.scans}</td>
                                                    <td className="px-3 py-2 text-center">
                                                        <button
                                                            onClick={() => handleCopy(idxObj.recommendation || `DROP INDEX CONCURRENTLY ${idxObj.schema}.${idxObj.index}`, "Drop SQL")}
                                                            className={`p-1 transition-colors ${isDark ? "text-slate-500 hover:text-red-400" : "text-slate-400 hover:text-red-500"}`}
                                                            title="Copy DROP SQL"
                                                        >
                                                            <Clipboard className="w-3.5 h-3.5" />
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {/* 4. Config Issue */}
                        {issue.type === "CONFIG" && extraData && (
                            <div className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className={`${isDark ? "bg-red-500/5 border-red-500/10" : "bg-red-50 border-red-100"} p-3 rounded-lg border`}>
                                        <span className={`text-[9px] uppercase font-black tracking-tighter mb-1 block ${isDark ? "text-red-500/70" : "text-red-400"}`}>Current Value</span>
                                        <span className={`text-lg font-mono font-black tabular-nums ${isDark ? "text-red-400" : "text-red-600"}`}>
                                            {Array.isArray(extraData) ? extraData[0].current_value : extraData.current_value}
                                        </span>
                                    </div>
                                    <div className={`${isDark ? "bg-emerald-500/5 border-emerald-500/10" : "bg-emerald-50 border-emerald-100"} p-3 rounded-lg border`}>
                                        <span className={`text-[9px] uppercase font-black tracking-tighter mb-1 block ${isDark ? "text-emerald-500/70" : "text-emerald-400"}`}>Recommended</span>
                                        <span className={`text-lg font-mono font-black tabular-nums ${isDark ? "text-emerald-400" : "text-emerald-600"}`}>
                                            {Array.isArray(extraData) ? 'Optimized' : (extraData.setting === 'work_mem' ? '16MB+' : extraData.setting === 'shared_buffers' ? '1GB+' : 'Optimized')}
                                        </span>
                                    </div>
                                </div>

                                <div className={`${isDark ? "bg-blue-500/5 border-blue-500/10" : "bg-blue-50 border-blue-100"} p-3 rounded-lg border`}>
                                    <div className="flex items-start gap-2">
                                        <Info className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isDark ? "text-blue-400" : "text-blue-500"}`} />
                                        <p className={`text-[11px] leading-relaxed ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                                            <span className={`font-bold uppercase text-[9px] mr-1.5 ${isDark ? "text-blue-400" : "text-blue-600"}`}>Context:</span>
                                            {Array.isArray(extraData)
                                                ? "Multiple configuration issues detected. Review the specific settings for optimal performance."
                                                : (extraData.setting === 'work_mem'
                                                    ? "Your workload involves heavy sorting; 4MB causes disk spills which drastically increase query latency."
                                                    : extraData.recommendation)
                                            }
                                        </p>
                                    </div>
                                </div>

                                <div className="space-y-1.5">
                                    <span className={`text-[10px] uppercase font-bold tracking-widest ${isDark ? "text-slate-500" : "text-slate-400"}`}>Apply Configuration Fix</span>
                                    <div className={`flex items-center gap-3 rounded-lg p-2.5 border group/fix ${isDark ? "bg-black/40 border-slate-800" : "bg-white border-slate-200"}`}>
                                        <code className={`text-[11px] font-mono flex-1 truncate ${isDark ? "text-emerald-400" : "text-emerald-600"}`}>
                                            {Array.isArray(extraData)
                                                ? "/* Multiple fixes needed */"
                                                : `ALTER SYSTEM SET ${extraData.setting} = ...; SELECT pg_reload_conf();`
                                            }
                                        </code>
                                        <button
                                            onClick={() => {
                                                const setting = Array.isArray(extraData) ? "config" : extraData.setting;
                                                const val = Array.isArray(extraData) ? "" : (extraData.setting === 'work_mem' ? '16MB' : '1GB');
                                                handleCopy(`ALTER SYSTEM SET ${setting} = '${val}'; SELECT pg_reload_conf();`, "Fix SQL");
                                            }}
                                            className={`p-1.5 rounded transition-colors ${isDark ? "bg-slate-800 hover:bg-slate-700 text-slate-400" : "bg-slate-100 hover:bg-slate-200 text-slate-500"}`}
                                        >
                                            <Clipboard className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Fallback for other issues */}
                        {!extraData && (
                            <p className={`text-xs leading-relaxed ${isDark ? "text-slate-300" : "text-slate-600"}`}>
                                {issue.description}
                            </p>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
