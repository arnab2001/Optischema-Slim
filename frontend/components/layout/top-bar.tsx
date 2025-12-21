"use client";

import { useAppStore } from "@/store/appStore";
import {
    RefreshCw,
    Play,
    Pause,
    Sun,
    Moon,
    Clock
} from "lucide-react";
import { useEffect, useState } from "react";
import { SlimVitals } from "./slim-vitals";

export function TopBar() {
    const { isLiveMode, setLiveMode, lastUpdated, setLastUpdated, theme, toggleTheme } = useAppStore();
    const [timeAgo, setTimeAgo] = useState("");

    // Calculate time ago
    useEffect(() => {
        const updateTimeAgo = () => {
            if (!lastUpdated) {
                setTimeAgo("");
                return;
            }

            const seconds = Math.floor((Date.now() - new Date(lastUpdated).getTime()) / 1000);

            if (seconds < 5) {
                setTimeAgo("just now");
            } else if (seconds < 60) {
                setTimeAgo(`${seconds}s ago`);
            } else if (seconds < 3600) {
                setTimeAgo(`${Math.floor(seconds / 60)}m ago`);
            } else {
                setTimeAgo(`${Math.floor(seconds / 3600)}h ago`);
            }
        };

        updateTimeAgo();
        const interval = setInterval(updateTimeAgo, 5000);
        return () => clearInterval(interval);
    }, [lastUpdated]);

    const handleRefresh = () => {
        setLastUpdated(new Date());
        // Emit a custom event that dashboard can listen to
        window.dispatchEvent(new CustomEvent("optischema:refresh"));
    };

    const isDark = theme === "dark";

    return (
        <header className={`h-14 flex items-center justify-between px-6 border-b ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"
            }`}>
            {/* Left: Live Mode Indicator */}
            <div className="flex items-center gap-4">
                <button
                    onClick={() => setLiveMode(!isLiveMode)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${isLiveMode
                        ? "bg-green-100 text-green-700 hover:bg-green-200"
                        : isDark
                            ? "bg-slate-700 text-slate-400 hover:bg-slate-600"
                            : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                        }`}
                >
                    {isLiveMode ? (
                        <>
                            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                            Live
                        </>
                    ) : (
                        <>
                            <Pause className="w-3 h-3" />
                            Paused
                        </>
                    )}
                </button>

                <SlimVitals />

                {lastUpdated && (
                    <div className={`flex items-center gap-1.5 text-xs ${isDark ? "text-slate-400" : "text-slate-500"
                        }`}>
                        <Clock className="w-3.5 h-3.5" />
                        <span>Updated {timeAgo}</span>
                    </div>
                )}
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-2">
                {/* Refresh Button */}
                <button
                    onClick={handleRefresh}
                    className={`p-2 rounded-lg transition-colors ${isDark
                        ? "text-slate-400 hover:text-white hover:bg-slate-700"
                        : "text-slate-500 hover:text-slate-700 hover:bg-slate-100"
                        }`}
                    title="Refresh data"
                >
                    <RefreshCw className="w-4 h-4" />
                </button>

                {/* Theme Toggle */}
                <button
                    onClick={toggleTheme}
                    className={`p-2 rounded-lg transition-colors ${isDark
                        ? "text-slate-400 hover:text-white hover:bg-slate-700"
                        : "text-slate-500 hover:text-slate-700 hover:bg-slate-100"
                        }`}
                    title={`Switch to ${isDark ? "light" : "dark"} mode`}
                >
                    {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                </button>
            </div>
        </header>
    );
}
