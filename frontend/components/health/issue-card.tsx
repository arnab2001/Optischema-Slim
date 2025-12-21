"use client";

import { useAppStore } from "@/store/appStore";
import { AlertTriangle, Database, Settings, Activity, ArrowRight, Eye, Play } from "lucide-react";

interface Issue {
    type: "QUERY" | "CONFIG" | "SCHEMA" | "SYSTEM";
    severity: "CRITICAL" | "WARNING" | "INFO";
    title: string;
    description: string;
    action_payload: string;
}

interface IssueCardProps {
    issue: Issue;
    onAction: (issue: Issue) => void;
}

export function IssueCard({ issue, onAction }: IssueCardProps) {
    const { theme } = useAppStore();
    const isDark = theme === "dark";

    // Icon & Color mapping
    const getIcon = () => {
        switch (issue.type) {
            case "QUERY": return () => (
                <div className="w-6 h-3 flex flex-col gap-1 justify-center">
                    <div className="w-full h-1.5 bg-red-500 rounded-full" />
                    <div className="w-2/3 h-1 bg-red-500/20 rounded-full" />
                </div>
            );
            case "CONFIG": return Settings;
            case "SCHEMA": return Database;
            default: return AlertTriangle;
        }
    };

    const getActionLabel = () => {
        switch (issue.type) {
            case "QUERY": return "Inspect";
            case "CONFIG": return "View Fix";
            case "SCHEMA": return "View SQL";
            default: return "Details";
        }
    };

    const getActionIcon = () => {
        switch (issue.type) {
            case "QUERY": return ArrowRight;
            case "CONFIG": return Play;
            case "SCHEMA": return Eye;
            default: return ArrowRight;
        }
    };

    const Icon = getIcon();
    const ActionIcon = getActionIcon();

    return (
        <div className={`group flex items-center gap-3 p-3 pr-4 rounded-xl border transition-all duration-200 ${isDark
            ? "bg-slate-800/30 border-slate-700/50 hover:bg-slate-800 hover:border-slate-600"
            : "bg-slate-50/50 border-slate-200 hover:bg-white hover:border-slate-300 hover:shadow-sm"
            }`}>
            {/* Icon Box */}
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${issue.severity === "CRITICAL"
                ? "bg-red-500/10 text-red-500"
                : issue.severity === "WARNING"
                    ? "bg-yellow-500/10 text-yellow-500"
                    : "bg-blue-500/10 text-blue-500"
                }`}>
                <Icon className="w-5 h-5" />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                    <h4 className={`text-sm font-bold truncate ${isDark ? "text-slate-200" : "text-slate-800"}`}>
                        {issue.title}
                    </h4>
                    {issue.severity === "CRITICAL" && (
                        <span className="text-[10px] font-bold bg-red-500 text-white px-1.5 rounded-sm">CRITICAL</span>
                    )}
                </div>
                <p className={`text-xs truncate ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                    {issue.description}
                </p>
            </div>

            {/* Action */}
            {issue.action_payload && (
                <button
                    onClick={() => onAction(issue)}
                    className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${issue.type === "QUERY"
                        ? "opacity-100 bg-blue-600 hover:bg-blue-500 text-white"
                        : `opacity-0 group-hover:opacity-100 ${isDark
                            ? "bg-slate-700 hover:bg-slate-600 text-slate-200"
                            : "bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 shadow-sm"
                        }`
                        }`}
                >
                    {getActionLabel()}
                    <ActionIcon className="w-3 h-3" />
                </button>
            )}
        </div>
    );
}
