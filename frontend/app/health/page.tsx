"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { HealthDoctor } from "@/components/health/health-doctor";
import { SchemaHealth } from "@/components/health/schema-health";
import { UnusedIndexes } from "@/components/health/unused-indexes";
import { useConnectionStore } from "@/store/connectionStore";
import { useAppStore } from "@/store/appStore";
import { Database, Stethoscope } from "lucide-react";

export default function HealthPage() {
    const { isConnected } = useConnectionStore();
    const { theme } = useAppStore();
    const isDark = theme === "dark";
    const [activeTab, setActiveTab] = useState<"runtime" | "schema" | "indexes">("runtime");

    return (
        <AppShell>
            <div className="max-w-6xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                        <Stethoscope className="w-5 h-5 text-blue-500" />
                    </div>
                    <div>
                        <h1 className={`text-2xl font-bold ${isDark ? "text-white" : "text-slate-900"}`}>Health & Maintenance</h1>
                        <p className={`text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                            Deep diagnostics for runtime performance, schema design, and index health.
                        </p>
                    </div>
                </div>

                {!isConnected ? (
                    <div className={`p-12 text-center rounded-2xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
                        <Database className={`w-12 h-12 mx-auto mb-4 ${isDark ? "text-slate-600" : "text-slate-300"}`} />
                        <h3 className={`text-lg font-medium mb-1 ${isDark ? "text-slate-200" : "text-slate-800"}`}>No Connection</h3>
                        <p className={isDark ? "text-slate-400" : "text-slate-500"}>
                            Connect to a database to analyze health vitals.
                        </p>
                    </div>
                ) : (
                    <>
                        {/* Tab Switcher */}
                        <div className={`p-1 rounded-lg flex gap-1 ${isDark ? "bg-slate-800" : "bg-slate-100"}`}>
                            <button
                                onClick={() => setActiveTab("runtime")}
                                className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all ${
                                    activeTab === "runtime"
                                        ? isDark
                                            ? "bg-slate-700 text-white shadow-sm"
                                            : "bg-white text-slate-800 shadow-sm"
                                        : "text-slate-500 hover:text-slate-400"
                                }`}
                            >
                                Runtime Health
                            </button>
                            <button
                                onClick={() => setActiveTab("schema")}
                                className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all ${
                                    activeTab === "schema"
                                        ? isDark
                                            ? "bg-slate-700 text-white shadow-sm"
                                            : "bg-white text-slate-800 shadow-sm"
                                        : "text-slate-500 hover:text-slate-400"
                                }`}
                            >
                                Schema Design
                            </button>
                            <button
                                onClick={() => setActiveTab("indexes")}
                                className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all ${
                                    activeTab === "indexes"
                                        ? isDark
                                            ? "bg-slate-700 text-white shadow-sm"
                                            : "bg-white text-slate-800 shadow-sm"
                                        : "text-slate-500 hover:text-slate-400"
                                }`}
                            >
                                Index Intelligence
                            </button>
                        </div>

                        {/* Tab Content */}
                        {activeTab === "runtime" ? (
                            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                                <HealthDoctor />
                            </div>
                        ) : activeTab === "schema" ? (
                            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                                <SchemaHealth />
                            </div>
                        ) : (
                            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                                <UnusedIndexes />
                            </div>
                        )}
                    </>
                )}
            </div>
        </AppShell>
    );
}
