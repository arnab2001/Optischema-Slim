"use client";

import { useAppStore } from "@/store/appStore";
import { ChevronRight, ChevronDown, Database, Activity, GitCommit, Layers, AlertTriangle } from "lucide-react";
import { useState } from "react";

interface PlanNodeProps {
    node: any;
    depth?: number;
    totalCost?: number;
}

// ── Bottleneck Detection ─────────────────────────────────────────────────────

interface Badge {
    label: string;
    color: string; // tailwind bg class
    textColor: string;
}

function detectBadges(node: any, rows: number): Badge[] {
    const badges: Badge[] = [];
    const type: string = node["Node Type"] || "";

    // Seq Scan on a table with many rows → missing index
    if (type === "Seq Scan" && rows > 500) {
        badges.push({ label: "Missing Index", color: "bg-red-500/20", textColor: "text-red-400" });
    }

    // Nested Loop with high row count → consider hash join
    if (type === "Nested Loop" && rows > 5000) {
        badges.push({ label: "Consider Hash Join", color: "bg-yellow-500/20", textColor: "text-yellow-400" });
    }

    // Sort node without an index → missing sort index
    if (type === "Sort" && !node["Index Name"]) {
        badges.push({ label: "Missing Sort Index", color: "bg-orange-500/20", textColor: "text-orange-400" });
    }

    // High rows removed by filter → poor selectivity
    const rowsRemoved = node["Rows Removed by Filter"] || 0;
    if (rowsRemoved > 0 && rows > 0 && rowsRemoved > rows * 5) {
        badges.push({ label: "Poor Selectivity", color: "bg-purple-500/20", textColor: "text-purple-400" });
    }

    return badges;
}

// ── Heat Map Color Logic ─────────────────────────────────────────────────────

function getHeatColor(costPercent: number): { bar: string; text: string; pulse: boolean } {
    if (costPercent >= 60) return { bar: "bg-red-500", text: "text-red-500", pulse: true };
    if (costPercent >= 30) return { bar: "bg-orange-500", text: "text-orange-400", pulse: false };
    if (costPercent >= 10) return { bar: "bg-yellow-500", text: "text-yellow-400", pulse: false };
    return { bar: "bg-green-500", text: "text-green-400", pulse: false };
}

// ── Main Component ───────────────────────────────────────────────────────────

export function PlanNode({ node, depth = 0, totalCost }: PlanNodeProps) {
    const { theme } = useAppStore();
    const isDark = theme === "dark";
    const [expanded, setExpanded] = useState(true);
    const [showTooltip, setShowTooltip] = useState(false);

    const hasChildren = node.Plans && node.Plans.length > 0;
    const cost = node["Total Cost"];
    const rows = node["Plan Rows"];
    const actualRows = node["Actual Rows"];
    const type = node["Node Type"];

    const effectiveTotalCost = depth === 0 ? cost : totalCost || cost;
    const costPercent = effectiveTotalCost > 0 ? (cost / effectiveTotalCost) * 100 : 0;

    const heat = getHeatColor(costPercent);
    const badges = detectBadges(node, rows);

    const getNodeIcon = (type: string) => {
        if (type.includes("Scan") || type.includes("Index")) return Database;
        if (type.includes("Join")) return GitCommit;
        if (type.includes("Sort") || type.includes("Aggregate") || type.includes("Group")) return Activity;
        return Layers;
    };

    const getNodeColorClass = (type: string) => {
        if (type.includes("Scan") || type.includes("Index")) return "bg-blue-500";
        if (type.includes("Join")) return "bg-yellow-500";
        if (type.includes("Sort") || type.includes("Aggregate") || type.includes("Group")) return "bg-purple-500";
        return "bg-slate-500";
    };

    const getNodeTextColorClass = (type: string) => {
        if (type.includes("Scan") || type.includes("Index")) return "text-blue-400";
        if (type.includes("Join")) return "text-yellow-400";
        if (type.includes("Sort") || type.includes("Aggregate") || type.includes("Group")) return "text-purple-400";
        return "text-slate-400";
    };

    const Icon = getNodeIcon(type);
    const accentColor = getNodeColorClass(type);
    const textColor = getNodeTextColorClass(type);

    // ── Tooltip data ─────────────────────────────────────────────────────────
    const sharedHit = node["Shared Hit Blocks"];
    const sharedRead = node["Shared Read Blocks"];
    const localHit = node["Local Hit Blocks"];
    const filterCond = node["Filter"];
    const rowsRemovedByFilter = node["Rows Removed by Filter"];
    const startupCost = node["Startup Cost"];

    return (
        <div className="font-mono text-[11px]">
            <div
                className={`group relative flex items-start gap-3 py-1 px-2 transition-all cursor-pointer hover:bg-white/5`}
                style={{ marginLeft: `${depth * 16}px` }}
                onClick={(e) => {
                    e.stopPropagation();
                    setExpanded(!expanded);
                }}
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
            >
                {/* Visual Cue - Vertical Bar */}
                <div className={`absolute left-0 top-0 bottom-0 w-0.5 opacity-40 group-hover:opacity-100 transition-opacity ${accentColor}`} />

                <button className={`mt-1 p-0.5 rounded hover:bg-slate-800 transition-colors ${hasChildren ? "opacity-100" : "opacity-0"}`}>
                    {expanded ? <ChevronDown className="w-3 h-3 text-slate-500" /> : <ChevronRight className="w-3 h-3 text-slate-500" />}
                </button>

                <Icon className={`w-3.5 h-3.5 mt-1 flex-shrink-0 ${textColor}`} />

                <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-2 truncate">
                            <span className={`font-bold ${textColor}`}>
                                {type}
                            </span>
                            {node["Relation Name"] && (
                                <span className={`text-slate-500 italic truncate`}>
                                    on {node["Relation Name"]}
                                </span>
                            )}
                            {/* Bottleneck Badges */}
                            {badges.map((badge, i) => (
                                <span
                                    key={i}
                                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${badge.color} ${badge.textColor} flex items-center gap-0.5`}
                                >
                                    <AlertTriangle className="w-2.5 h-2.5" />
                                    {badge.label}
                                </span>
                            ))}
                        </div>

                        {/* Cost & Rows - Heat Map */}
                        <div className="flex items-center gap-6 flex-shrink-0">
                            <div className="flex flex-col items-end">
                                <span className={`font-bold ${heat.text}`}>
                                    {costPercent.toFixed(1)}%
                                </span>
                                <div className="w-20 h-1 bg-slate-800 rounded-full mt-1 overflow-hidden">
                                    <div
                                        className={`h-full ${heat.bar} ${heat.pulse ? "animate-pulse" : ""}`}
                                        style={{ width: `${Math.min(costPercent, 100)}%` }}
                                    />
                                </div>
                            </div>
                            <div className="w-16 text-right text-slate-400 font-bold">
                                {rows > 1000 ? `${(rows / 1000).toFixed(1)}k` : rows} <span className="text-[9px] opacity-50">rows</span>
                            </div>
                        </div>
                    </div>

                    {/* Filter condition */}
                    {node["Filter"] && (
                        <div className={`mt-1 py-0.5 px-1.5 rounded bg-black/40 text-[10px] text-slate-500 border border-slate-800/50 inline-block`}>
                            <span className="text-red-400/70 font-bold mr-1">FILTER:</span>
                            {node["Filter"]}
                        </div>
                    )}
                    {node["Index Name"] && (
                        <div className={`mt-1 py-0.5 px-1.5 rounded bg-blue-500/5 text-[10px] text-blue-400/80 border border-blue-500/10 inline-block`}>
                            <span className="text-blue-500 font-bold mr-1">INDEX:</span>
                            {node["Index Name"]}
                        </div>
                    )}
                </div>

                {/* Tooltip on hover */}
                {showTooltip && (
                    <div
                        className="absolute left-full top-0 ml-2 z-50 w-64 p-3 rounded-lg border bg-slate-900 border-slate-700 shadow-xl text-[10px] space-y-1.5"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="font-bold text-slate-300 text-[11px] mb-2">{type}</div>

                        <div className="flex justify-between">
                            <span className="text-slate-500">Cost</span>
                            <span className="text-slate-300">{startupCost?.toFixed(1)}..{cost?.toFixed(1)}</span>
                        </div>

                        <div className="flex justify-between">
                            <span className="text-slate-500">Est. Rows</span>
                            <span className="text-slate-300">{rows?.toLocaleString()}</span>
                        </div>

                        {actualRows != null && (
                            <div className="flex justify-between">
                                <span className="text-slate-500">Actual Rows</span>
                                <span className={actualRows > rows * 5 ? "text-red-400 font-bold" : "text-slate-300"}>
                                    {actualRows.toLocaleString()}
                                    {rows > 0 && actualRows !== rows && (
                                        <span className="text-slate-500 ml-1">
                                            ({((actualRows / rows) * 100).toFixed(0)}%)
                                        </span>
                                    )}
                                </span>
                            </div>
                        )}

                        {rowsRemovedByFilter != null && rowsRemovedByFilter > 0 && (
                            <div className="flex justify-between">
                                <span className="text-slate-500">Rows Removed</span>
                                <span className="text-orange-400">{rowsRemovedByFilter.toLocaleString()}</span>
                            </div>
                        )}

                        {(sharedHit != null || sharedRead != null) && (
                            <div className="flex justify-between">
                                <span className="text-slate-500">Buffers</span>
                                <span className="text-slate-300">
                                    {sharedHit || 0} hit / {sharedRead || 0} read
                                </span>
                            </div>
                        )}

                        {localHit != null && (
                            <div className="flex justify-between">
                                <span className="text-slate-500">Local Buffers</span>
                                <span className="text-slate-300">{localHit} hit</span>
                            </div>
                        )}

                        {filterCond && (
                            <div className="pt-1.5 mt-1.5 border-t border-slate-700">
                                <span className="text-slate-500 block mb-0.5">Filter</span>
                                <code className="text-slate-400 break-all">{filterCond}</code>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {hasChildren && expanded && (
                <div className="relative">
                    {/* Connection line */}
                    <div className="absolute left-[7px] top-0 bottom-0 w-px bg-slate-800" style={{ transform: `translateX(${depth * 16}px)` }} />
                    <div className="space-y-0.5">
                        {node.Plans.map((child: any, i: number) => (
                            <PlanNode
                                key={i}
                                node={child}
                                depth={depth + 1}
                                totalCost={effectiveTotalCost}
                            />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
