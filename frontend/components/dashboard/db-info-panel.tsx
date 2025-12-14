"use client";

import { useState, useEffect } from "react";
import { useAppStore } from "@/store/appStore";
import {
    Database,
    HardDrive,
    Table2,
    CheckCircle2,
    XCircle,
    Loader2,
    Server,
    Package
} from "lucide-react";

interface Extension {
    name: string;
    version: string;
}

interface DbInfo {
    version: string;
    version_full: string;
    database_name: string;
    database_size: string;
    table_count: number;
    extensions: Extension[];
    has_pg_stat_statements: boolean;
    has_hypopg: boolean;
    error?: string;
}

export function DbInfoPanel() {
    const [info, setInfo] = useState<DbInfo | null>(null);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(false);
    const { theme } = useAppStore();
    const isDark = theme === "dark";

    const fetchDbInfo = async () => {
        setLoading(true);
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
            const res = await fetch(`${apiUrl}/api/metrics/db-info`);
            const data = await res.json();
            setInfo(data);
        } catch (e) {
            console.error("Failed to fetch DB info:", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDbInfo();
    }, []);

    if (loading) {
        return (
            <div className={`rounded-xl border p-4 ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                    <span className={`text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                        Loading database info...
                    </span>
                </div>
            </div>
        );
    }

    if (!info || info.error) {
        return (
            <div className={`rounded-xl border p-4 ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                <div className="flex items-center gap-2 text-slate-500">
                    <Database className="w-4 h-4" />
                    <span className="text-sm">Database info unavailable</span>
                </div>
            </div>
        );
    }

    const keyExtensions = ["pg_stat_statements", "hypopg"];
    const otherExtensions = info.extensions.filter(e => !keyExtensions.includes(e.name));

    return (
        <div className={`rounded-xl border transition-all ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
            {/* Header - Always Visible */}
            <div
                className="p-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${isDark ? "bg-blue-900/30" : "bg-blue-50"}`}>
                            <Server className={`w-4 h-4 ${isDark ? "text-blue-400" : "text-blue-600"}`} />
                        </div>
                        <div>
                            <p className={`font-medium ${isDark ? "text-white" : "text-slate-800"}`}>
                                {info.database_name}
                            </p>
                            <p className={`text-xs ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                PostgreSQL {info.version}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        {/* Extension Status Pills */}
                        <div className="flex gap-1.5">
                            <span
                                className={`px-2 py-0.5 rounded text-xs font-medium ${info.has_pg_stat_statements
                                        ? isDark ? "bg-green-900/30 text-green-400" : "bg-green-100 text-green-700"
                                        : isDark ? "bg-red-900/30 text-red-400" : "bg-red-100 text-red-700"
                                    }`}
                                title="pg_stat_statements extension"
                            >
                                pg_stat ✓
                            </span>
                            <span
                                className={`px-2 py-0.5 rounded text-xs font-medium ${info.has_hypopg
                                        ? isDark ? "bg-green-900/30 text-green-400" : "bg-green-100 text-green-700"
                                        : isDark ? "bg-yellow-900/30 text-yellow-400" : "bg-yellow-100 text-yellow-700"
                                    }`}
                                title="HypoPG extension"
                            >
                                HypoPG {info.has_hypopg ? "✓" : "—"}
                            </span>
                        </div>
                        <span className={`text-xs ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                            {expanded ? "▲" : "▼"}
                        </span>
                    </div>
                </div>
            </div>

            {/* Expanded Details */}
            {expanded && (
                <div className={`border-t px-4 pb-4 ${isDark ? "border-slate-700" : "border-slate-200"}`}>
                    {/* Stats Grid */}
                    <div className="grid grid-cols-3 gap-4 py-4">
                        <div className="text-center">
                            <div className="flex items-center justify-center gap-1.5 mb-1">
                                <HardDrive className={`w-3.5 h-3.5 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                <span className={`text-xs ${isDark ? "text-slate-400" : "text-slate-500"}`}>Size</span>
                            </div>
                            <p className={`font-semibold ${isDark ? "text-white" : "text-slate-800"}`}>
                                {info.database_size}
                            </p>
                        </div>
                        <div className="text-center">
                            <div className="flex items-center justify-center gap-1.5 mb-1">
                                <Table2 className={`w-3.5 h-3.5 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                <span className={`text-xs ${isDark ? "text-slate-400" : "text-slate-500"}`}>Tables</span>
                            </div>
                            <p className={`font-semibold ${isDark ? "text-white" : "text-slate-800"}`}>
                                {info.table_count}
                            </p>
                        </div>
                        <div className="text-center">
                            <div className="flex items-center justify-center gap-1.5 mb-1">
                                <Package className={`w-3.5 h-3.5 ${isDark ? "text-slate-400" : "text-slate-500"}`} />
                                <span className={`text-xs ${isDark ? "text-slate-400" : "text-slate-500"}`}>Extensions</span>
                            </div>
                            <p className={`font-semibold ${isDark ? "text-white" : "text-slate-800"}`}>
                                {info.extensions.length}
                            </p>
                        </div>
                    </div>

                    {/* Extensions List */}
                    <div className={`border-t pt-3 ${isDark ? "border-slate-700" : "border-slate-200"}`}>
                        <p className={`text-xs font-medium mb-2 ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                            Installed Extensions
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                            {info.extensions.map((ext) => (
                                <span
                                    key={ext.name}
                                    className={`px-2 py-1 rounded text-xs ${keyExtensions.includes(ext.name)
                                            ? isDark ? "bg-blue-900/30 text-blue-400" : "bg-blue-100 text-blue-700"
                                            : isDark ? "bg-slate-700 text-slate-300" : "bg-slate-100 text-slate-600"
                                        }`}
                                    title={`Version: ${ext.version}`}
                                >
                                    {ext.name}
                                </span>
                            ))}
                        </div>
                    </div>

                    {/* Full Version */}
                    <div className={`border-t pt-3 mt-3 ${isDark ? "border-slate-700" : "border-slate-200"}`}>
                        <p className={`text-xs font-mono break-all ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                            {info.version_full}
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
