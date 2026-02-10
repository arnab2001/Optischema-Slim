"use client";

import { AppShell } from "@/components/layout/app-shell";
import { useAppStore } from "@/store/appStore";
import { Save, Zap, Clock, Trash2 } from "lucide-react";
import { useState, useEffect } from "react";

interface SavedOptimization {
    id: string;
    query: string;
    suggestion: string;
    sql?: string;
    createdAt: string;
    tier: "verified" | "estimated" | "advisory";
}

export default function SavedPage() {
    const { theme } = useAppStore();
    const isDark = theme === "dark";
    const [saved, setSaved] = useState<SavedOptimization[]>([]);
    const [loading, setLoading] = useState(true);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";

    useEffect(() => {
        fetchSaved();
    }, []);

    const fetchSaved = async () => {
        try {
            const res = await fetch(`${apiUrl}/api/optimizations/saved`);
            if (res.ok) {
                const data = await res.json();
                setSaved(data);
            }
        } catch (e) {
            console.error("Failed to fetch saved optimizations:", e);
        } finally {
            setLoading(false);
        }
    };

    const deleteSaved = async (id: string) => {
        try {
            await fetch(`${apiUrl}/api/optimizations/saved/${id}`, { method: "DELETE" });
            setSaved(saved.filter(s => s.id !== id));
        } catch (e) {
            console.error("Failed to delete:", e);
        }
    };

    const getTierBadge = (tier: string) => {
        switch (tier) {
            case "verified":
                return <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">Verified</span>;
            case "estimated":
                return <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-700 rounded-full">Estimated</span>;
            default:
                return <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">Advisory</span>;
        }
    };

    return (
        <AppShell>
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <h1 className={`text-2xl font-bold ${isDark ? "text-white" : "text-slate-800"}`}>
                        <Save className="inline-block w-6 h-6 mr-2 -mt-1" />
                        Saved Optimizations
                    </h1>
                </div>

                {loading ? (
                    <div className="flex justify-center py-12">
                        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    </div>
                ) : saved.length === 0 ? (
                    <div className={`text-center py-12 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"
                        }`}>
                        <Zap className={`w-12 h-12 mx-auto mb-4 ${isDark ? "text-slate-600" : "text-slate-300"}`} />
                        <p className={isDark ? "text-slate-400" : "text-slate-500"}>
                            No saved optimizations yet
                        </p>
                        <p className={`text-sm mt-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                            Analyze queries and save the results to view them here
                        </p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {saved.map((opt) => (
                            <div
                                key={opt.id}
                                className={`p-4 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"
                                    }`}
                            >
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-2">
                                        {getTierBadge(opt.tier)}
                                        <span className={`text-xs ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                            <Clock className="inline-block w-3 h-3 mr-1" />
                                            {new Date(opt.createdAt).toLocaleDateString()}
                                        </span>
                                    </div>
                                    <button
                                        onClick={() => deleteSaved(opt.id)}
                                        className="p-1.5 text-red-500 hover:bg-red-50 rounded"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>

                                <pre className={`p-3 rounded-lg text-xs font-mono mb-3 overflow-x-auto ${isDark ? "bg-slate-900 text-slate-300" : "bg-slate-100 text-slate-700"
                                    }`}>
                                    {opt.query.substring(0, 200)}...
                                </pre>

                                <p className={`text-sm ${isDark ? "text-slate-300" : "text-slate-600"}`}>
                                    {opt.suggestion}
                                </p>

                                {opt.sql && (
                                    <pre className={`mt-3 p-3 rounded-lg text-xs font-mono ${isDark ? "bg-green-900/30 text-green-300" : "bg-green-50 text-green-700"
                                        }`}>
                                        {opt.sql}
                                    </pre>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </AppShell>
    );
}
