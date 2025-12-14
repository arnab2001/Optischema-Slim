"use client";

import { useAppStore } from "@/store/appStore";
import { Info } from "lucide-react";
import { useState } from "react";

interface SystemQueryToggleProps {
    value: boolean;
    onChange: (value: boolean) => void;
}

export function SystemQueryToggle({ value, onChange }: SystemQueryToggleProps) {
    const { theme } = useAppStore();
    const isDark = theme === "dark";
    const [showTooltip, setShowTooltip] = useState(false);

    // Save preference to localStorage when changed
    const handleToggle = (newValue: boolean) => {
        onChange(newValue);
        localStorage.setItem("optischema_show_system_queries", String(newValue));
    };

    return (
        <div className="flex items-center gap-2 relative">
            <label className="flex items-center gap-2 cursor-pointer">
                <div className="relative inline-flex items-center">
                    <input
                        type="checkbox"
                        checked={value}
                        onChange={(e) => handleToggle(e.target.checked)}
                        className="sr-only peer"
                    />
                    <div className={`w-11 h-6 rounded-full transition-colors duration-200 ${
                        value
                            ? "bg-blue-600"
                            : isDark
                                ? "bg-slate-700"
                                : "bg-slate-300"
                    } peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 peer-focus:ring-offset-2`}>
                        <div className={`absolute top-[2px] left-[2px] w-5 h-5 bg-white rounded-full transition-transform duration-200 ${
                            value ? "translate-x-5" : "translate-x-0"
                        }`} />
                    </div>
                </div>
                <span className={`text-xs font-medium ${isDark ? "text-slate-300" : "text-slate-700"}`}>
                    Show System Queries
                </span>
            </label>
            
            <div
                className="relative"
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
            >
                <Info className={`w-3.5 h-3.5 ${isDark ? "text-slate-500" : "text-slate-400"} cursor-help`} />
                
                {showTooltip && (
                    <div className={`absolute left-0 top-6 w-64 p-3 rounded-lg border shadow-lg z-50 ${
                        isDark
                            ? "bg-slate-800 border-slate-700"
                            : "bg-white border-slate-200"
                    }`}>
                        <p className={`text-xs font-semibold mb-1 ${isDark ? "text-slate-300" : "text-slate-700"}`}>
                            System Queries
                        </p>
                        <p className={`text-xs leading-relaxed ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                            When enabled, includes transaction control queries (COMMIT, ROLLBACK, BEGIN) and system queries. 
                            Useful for detecting "commit storms" and other transaction-related performance issues.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}

