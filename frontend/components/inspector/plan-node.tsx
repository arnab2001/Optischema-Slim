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
        if (type.includes("Scan")) return Database;
        if (type.includes("Join")) return GitCommit;
        if (type.includes("Sort") || type.includes("Aggregate")) return Activity;
        return Layers;
    };

    const Icon = getNodeIcon(type);

    return (
        <div className="font-mono text-xs">
            <div
                className={`flex items-start gap-2 py-1.5 px-2 rounded hover:bg-opacity-50 transition-colors cursor-pointer ${isDark ? "hover:bg-slate-800" : "hover:bg-slate-100"
                    } ${isExpensive ? (isDark ? "bg-red-900/10" : "bg-red-50") : ""}`}
                style={{ marginLeft: `${depth * 16}px` }}
                onClick={(e) => {
                    e.stopPropagation();
                    setExpanded(!expanded);
                }}
            >
                <button className={`mt-0.5 p-0.5 rounded hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors ${hasChildren ? "opacity-100" : "opacity-0"}`}>
                    {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                </button>

                <Icon className={`w-4 h-4 mt-0.5 ${isExpensive ? "text-red-500" : isDark ? "text-slate-400" : "text-slate-500"
                    }`} />

                <div className="flex-1">
                    <div className="flex items-center gap-2">
                        <span className={`font-semibold ${isDark ? "text-slate-200" : "text-slate-700"} ${isHighCostNode ? "text-yellow-500 dark:text-yellow-400" : ""}`}>
                            {type}
                        </span>
                        {node["Relation Name"] && (
                            <span className={`text-slate-500 italic`}>
                                on {node["Relation Name"]}
                            </span>
                        )}
                        {/* Cost Badge */}
                        <div className={`ml-auto flex items-center gap-4`}>
                            <div className="flex flex-col items-end w-24">
                                <span className={`font-medium ${isExpensive ? "text-red-500" : "text-slate-500"}`}>
                                    {cost.toFixed(1)}
                                </span>
                                <div className="w-16 h-1 bg-slate-200 dark:bg-slate-700 rounded-full mt-1 overflow-hidden">
                                    <div
                                        className={`h-full ${isExpensive ? "bg-red-500" : "bg-blue-500"}`}
                                        style={{ width: `${Math.min(costPercent, 100)}%` }}
                                    />
                                </div>
                            </div>
                            <div className="w-16 text-right text-slate-500">
                                {rows > 1000 ? `${(rows / 1000).toFixed(1)}k` : rows} rows
                            </div>
                        </div>
                    </div>
                    {/* Filter condition often contains useful info */}
                    {node["Filter"] && (
                        <div className={`mt-1 text-[10px] ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                            Filter: {node["Filter"]}
                        </div>
                    )}
                </div>
            </div>

            {hasChildren && expanded && (
                <div className="border-l border-slate-200 dark:border-slate-800 ml-[11px]">
                    {node.Plans.map((child: any, i: number) => (
                        <PlanNode
                            key={i}
                            node={child}
                            depth={depth + 1}
                            totalCost={effectiveTotalCost}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
