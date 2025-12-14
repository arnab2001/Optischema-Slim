"use client";

import { useAppStore } from "@/store/appStore";
import { Search, X } from "lucide-react";
import { SystemQueryToggle } from "@/components/SystemQueryToggle";

interface FilterBarProps {
    searchTerm: string;
    onSearchChange: (value: string) => void;
    activeFilter: string | null;
    onFilterChange: (filter: string | null) => void;
    totalCount: number;
    displayCount: number;
    sampleSize: number;
    onSampleSizeChange: (size: number) => void;
    includeSystem: boolean;
    onIncludeSystemChange: (value: boolean) => void;
    onReset: () => void;
}

const filters = [
    { id: "slow", label: "Slow Queries (>500ms)", color: "red" },
    { id: "high-freq", label: "High Frequency (>1k)", color: "yellow" },
    { id: "full-scan", label: "Full Scans", color: "orange" },
];

const sampleSizes = [10, 25, 50, 100, 200, 500];

export function FilterBar({
    searchTerm,
    onSearchChange,
    activeFilter,
    onFilterChange,
    totalCount,
    displayCount,
    sampleSize,
    onSampleSizeChange,
    includeSystem,
    onIncludeSystemChange,
    onReset,
}: FilterBarProps) {
    const { theme } = useAppStore();
    const isDark = theme === "dark";

    return (
        <div className={`flex flex-col sm:flex-row gap-4 p-4 rounded-xl border ${isDark
            ? "bg-slate-800 border-slate-700"
            : "bg-white border-slate-200"
            }`}>
            {/* Search */}
            <div className="relative flex-1">
                <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${isDark ? "text-slate-500" : "text-slate-400"
                    }`} />
                <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => onSearchChange(e.target.value)}
                    placeholder="Search queries by table name or SQL..."
                    className={`w-full pl-10 pr-4 py-2 rounded-lg border text-sm ${isDark
                        ? "bg-slate-700 border-slate-600 text-white placeholder:text-slate-500"
                        : "bg-slate-50 border-slate-200 text-slate-800 placeholder:text-slate-400"
                        } focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none`}
                />
                {searchTerm && (
                    <button
                        onClick={() => onSearchChange("")}
                        className={`absolute right-3 top-1/2 -translate-y-1/2 ${isDark ? "text-slate-500 hover:text-slate-300" : "text-slate-400 hover:text-slate-600"
                            }`}
                    >
                        <X className="w-4 h-4" />
                    </button>
                )}
            </div>

            {/* Filter Pills + Stats + Sample Size */}
            <div className="flex items-center gap-4 flex-wrap">
                {/* Filter Pills */}
                <div className="flex gap-2">
                    {filters.map((filter) => {
                        const isActive = activeFilter === filter.id;

                        return (
                            <button
                                key={filter.id}
                                onClick={() => onFilterChange(isActive ? null : filter.id)}
                                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-150 ${isActive
                                    ? filter.color === "red"
                                        ? "bg-red-500/20 text-red-400 border border-red-500/40 shadow-sm shadow-red-500/10"
                                        : filter.color === "yellow"
                                            ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500/40 shadow-sm shadow-yellow-500/10"
                                            : "bg-orange-500/20 text-orange-400 border border-orange-500/40 shadow-sm shadow-orange-500/10"
                                    : isDark
                                        ? "bg-slate-700/50 text-slate-400 hover:text-slate-200 hover:bg-slate-600 border border-slate-600"
                                        : "bg-slate-100 text-slate-500 hover:text-slate-700 hover:bg-slate-200 border border-slate-200"
                                    }`}
                            >
                                {filter.label}
                            </button>
                        );
                    })}
                </div>

                {/* Divider */}
                <div className={`h-6 w-px ${isDark ? "bg-slate-700" : "bg-slate-200"}`} />

                {/* System Query Toggle */}
                <SystemQueryToggle value={includeSystem} onChange={onIncludeSystemChange} />

                {/* Divider */}
                <div className={`h-6 w-px ${isDark ? "bg-slate-700" : "bg-slate-200"}`} />

                {/* Stats Indicator */}
                <span className={`text-xs whitespace-nowrap ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                    Showing <span className="font-medium">{displayCount}</span> of <span className="font-medium">{totalCount}</span>
                </span>

                {/* Sample Size Selector */}
                <select
                    value={sampleSize}
                    onChange={(e) => onSampleSizeChange(Number(e.target.value))}
                    className={`text-xs px-2 py-1.5 rounded border ${isDark
                        ? "bg-slate-700 border-slate-600 text-slate-300"
                        : "bg-white border-slate-200 text-slate-700"
                        } focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none`}
                >
                    {sampleSizes.map(size => (
                        <option key={size} value={size}>
                            Top {size}
                        </option>
                    ))}
                </select>

                {/* Reset Button */}
                <button
                    onClick={onReset}
                    title="Reset Statistics (pg_stat_statements_reset)"
                    className={`p-1.5 rounded border transition-colors ${isDark
                        ? "bg-slate-700 border-slate-600 text-slate-400 hover:text-red-400 hover:border-red-900/50"
                        : "bg-white border-slate-200 text-slate-500 hover:text-red-600 hover:border-red-200"
                        }`}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                        <path d="M3 3v5h5" />
                    </svg>
                </button>
            </div>
        </div>
    );
}
