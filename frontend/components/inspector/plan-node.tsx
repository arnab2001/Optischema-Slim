"use client";

import { useAppStore } from "@/store/appStore";
import { ChevronRight, ChevronDown, Database, Activity, GitCommit, Layers } from "lucide-react";
import { useState } from "react";

interface PlanNodeProps {
    node: any;
    depth?: number;
    totalCost?: number; // Pass root total cost to calculate relative cost
}

export function PlanNode({ node, depth = 0, totalCost }: PlanNodeProps) {
    const { theme } = useAppStore();
    const isDark = theme === "dark";
    const [expanded, setExpanded] = useState(true);

    const hasChildren = node.Plans && node.Plans.length > 0;
    const cost = node["Total Cost"];
    const rows = node["Plan Rows"];
    const type = node["Node Type"];

    // Calculate percentage if totalCost is provided, else assume this is root or relative to something
    // If depth is 0, this IS the root, so totalCost is this node's cost
    const effectiveTotalCost = depth === 0 ? cost : totalCost || cost;
    const costPercent = effectiveTotalCost > 0 ? (cost / effectiveTotalCost) * 100 : 0;

    // Determine color based on cost
    const isExpensive = cost > 1000;
    const isHighCostNode = costPercent > 30; // 30% of query cost

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

    return (
        <div className="font-mono text-[11px]">
            <div
                className={`group relative flex items-start gap-3 py-1 px-2 transition-all cursor-pointer hover:bg-white/5`}
                style={{ marginLeft: `${depth * 16}px` }}
                onClick={(e) => {
                    e.stopPropagation();
                    setExpanded(!expanded);
                }}
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
                        </div>

                        {/* Cost & Rows */}
                        <div className="flex items-center gap-6 flex-shrink-0">
                            <div className="flex flex-col items-end">
                                <span className={`font-bold ${isHighCostNode ? "text-red-500" : "text-slate-300"}`}>
                                    {costPercent.toFixed(1)}%
                                </span>
                                <div className="w-20 h-1 bg-slate-800 rounded-full mt-1 overflow-hidden">
                                    <div
                                        className={`h-full ${isHighCostNode ? "bg-red-500 animate-pulse" : accentColor}`}
                                        style={{ width: `${Math.min(costPercent, 100)}%` }}
                                    />
                                </div>
                            </div>
                            <div className="w-16 text-right text-slate-400 font-bold">
                                {rows > 1000 ? `${(rows / 1000).toFixed(1)}k` : rows} <span className="text-[9px] opacity-50">rows</span>
                            </div>
                        </div>
                    </div>

                    {/* Filter condition often contains useful info */}
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
