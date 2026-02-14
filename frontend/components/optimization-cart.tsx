"use client";

import { useState } from "react";
import { ShoppingCart, X, Trash2, Play, Download, ChevronUp, ChevronDown, AlertTriangle } from "lucide-react";
import { useCartStore, CartItem } from "@/store/cartStore";
import { useAppStore } from "@/store/appStore";
import { toast } from "sonner";

export function OptimizationCart() {
    const { theme } = useAppStore();
    const isDark = theme === "dark";
    const { items, removeItem, clearCart, totalEstimatedImprovement } = useCartStore();
    const [isOpen, setIsOpen] = useState(false);
    const [isApplying, setIsApplying] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);

    const apiUrl = import.meta.env.VITE_API_URL || "";

    const handleApplyAll = async () => {
        setShowConfirm(false);
        setIsApplying(true);

        try {
            // Sync cart to backend first
            for (const item of items) {
                await fetch(`${apiUrl}/api/cart/add`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        item: {
                            id: item.id,
                            type: item.type,
                            sql: item.sql,
                            description: item.description,
                            table: item.table,
                            estimated_improvement: item.estimatedImprovement,
                            source: item.source,
                        },
                    }),
                });
            }

            const res = await fetch(`${apiUrl}/api/cart/apply`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tenant_id: "default" }),
            });

            const data = await res.json();
            if (data.success) {
                toast.success(`Applied ${data.applied} optimizations successfully`);
                clearCart();
                setIsOpen(false);
            } else {
                toast.error(data.detail || "Apply failed");
            }
        } catch (e) {
            toast.error("Failed to apply optimizations");
        } finally {
            setIsApplying(false);
        }
    };

    const handleExport = async () => {
        try {
            // Sync cart to backend
            // Clear backend cart first to avoid stale items
            await fetch(`${apiUrl}/api/cart/clear`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tenant_id: "default" }),
            });

            for (const item of items) {
                await fetch(`${apiUrl}/api/cart/add`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        item: {
                            id: item.id,
                            type: item.type,
                            sql: item.sql,
                            description: item.description,
                            table: item.table,
                            estimated_improvement: item.estimatedImprovement,
                            source: item.source,
                        },
                    }),
                });
            }

            const res = await fetch(`${apiUrl}/api/cart/export?tenant_id=default`);
            if (!res.ok) {
                toast.error("Export failed");
                return;
            }

            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `optischema_migration_${new Date().toISOString().replace(/[:.]/g, "")}.sql`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            toast.success("Migration script exported");
        } catch (e) {
            toast.error("Export failed");
        }
    };

    const getTypeBadgeColor = (type: string) => {
        switch (type) {
            case "index": return "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300";
            case "rewrite": return "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300";
            case "drop": return "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300";
            default: return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300";
        }
    };

    if (items.length === 0) return null;

    return (
        <div className="fixed bottom-6 right-6 z-50">
            {/* Expanded Panel */}
            {isOpen && (
                <div className={`mb-3 w-96 rounded-xl shadow-2xl border overflow-hidden ${isDark
                    ? "bg-slate-900 border-slate-700"
                    : "bg-white border-slate-200"
                    }`}>
                    {/* Panel Header */}
                    <div className={`flex items-center justify-between px-4 py-3 border-b ${isDark ? "border-slate-700 bg-slate-800/50" : "border-slate-200 bg-slate-50"
                        }`}>
                        <div className="flex items-center gap-2">
                            <ShoppingCart className="w-4 h-4 text-blue-500" />
                            <span className={`text-sm font-bold ${isDark ? "text-white" : "text-slate-800"}`}>
                                Optimization Cart
                            </span>
                            <span className="text-xs text-slate-500">({items.length})</span>
                        </div>
                        <button
                            onClick={() => setIsOpen(false)}
                            className={`p-1 rounded hover:bg-opacity-10 ${isDark ? "text-slate-400 hover:bg-white" : "text-slate-500 hover:bg-black"}`}
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>

                    {/* Items List */}
                    <div className="max-h-72 overflow-y-auto">
                        {items.map((item) => (
                            <div
                                key={item.id}
                                className={`flex items-start gap-3 px-4 py-3 border-b last:border-b-0 ${isDark ? "border-slate-800 hover:bg-slate-800/40" : "border-slate-100 hover:bg-slate-50"
                                    }`}
                            >
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${getTypeBadgeColor(item.type)}`}>
                                            {item.type}
                                        </span>
                                        {item.estimatedImprovement != null && item.estimatedImprovement > 0 && (
                                            <span className="text-[10px] text-green-500 font-bold">
                                                +{item.estimatedImprovement}%
                                            </span>
                                        )}
                                    </div>
                                    <p className={`text-xs truncate ${isDark ? "text-slate-300" : "text-slate-700"}`}>
                                        {item.description}
                                    </p>
                                    <p className={`text-[10px] font-mono truncate mt-0.5 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                        {item.sql}
                                    </p>
                                </div>
                                <button
                                    onClick={() => removeItem(item.id)}
                                    className="p-1 text-slate-400 hover:text-red-500 transition-colors flex-shrink-0"
                                >
                                    <Trash2 className="w-3.5 h-3.5" />
                                </button>
                            </div>
                        ))}
                    </div>

                    {/* Summary & Actions */}
                    <div className={`px-4 py-3 border-t space-y-3 ${isDark ? "border-slate-700 bg-slate-800/30" : "border-slate-200 bg-slate-50/50"}`}>
                        {totalEstimatedImprovement() > 0 && (
                            <div className={`text-xs ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                Total estimated improvement: <span className="font-bold text-green-500">+{totalEstimatedImprovement()}%</span>
                            </div>
                        )}

                        {/* Confirmation Dialog */}
                        {showConfirm && (
                            <div className={`p-3 rounded-lg border ${isDark ? "bg-yellow-900/20 border-yellow-700/50" : "bg-yellow-50 border-yellow-200"}`}>
                                <div className="flex items-start gap-2 mb-2">
                                    <AlertTriangle className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />
                                    <p className={`text-xs ${isDark ? "text-yellow-300" : "text-yellow-700"}`}>
                                        This will execute {items.length} SQL statement{items.length > 1 ? "s" : ""} in a single transaction on your connected database. Are you sure?
                                    </p>
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={handleApplyAll}
                                        disabled={isApplying}
                                        className="flex-1 py-1.5 text-xs font-bold bg-green-600 hover:bg-green-500 text-white rounded-lg disabled:opacity-50 flex items-center justify-center gap-1"
                                    >
                                        {isApplying ? (
                                            <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                        ) : (
                                            <Play className="w-3 h-3" />
                                        )}
                                        Confirm Apply
                                    </button>
                                    <button
                                        onClick={() => setShowConfirm(false)}
                                        className={`px-3 py-1.5 text-xs font-bold rounded-lg ${isDark ? "bg-slate-700 text-slate-300 hover:bg-slate-600" : "bg-slate-200 text-slate-700 hover:bg-slate-300"}`}
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        )}

                        {!showConfirm && (
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setShowConfirm(true)}
                                    className="flex-1 py-2 text-xs font-bold bg-green-600 hover:bg-green-500 text-white rounded-lg flex items-center justify-center gap-1.5 shadow-lg shadow-green-500/20"
                                >
                                    <Play className="w-3.5 h-3.5" />
                                    Apply All
                                </button>
                                <button
                                    onClick={handleExport}
                                    className={`py-2 px-3 text-xs font-bold rounded-lg flex items-center gap-1.5 ${isDark
                                        ? "bg-slate-700 text-slate-300 hover:bg-slate-600"
                                        : "bg-slate-200 text-slate-700 hover:bg-slate-300"
                                        }`}
                                >
                                    <Download className="w-3.5 h-3.5" />
                                    Export SQL
                                </button>
                                <button
                                    onClick={() => { clearCart(); setIsOpen(false); }}
                                    className="py-2 px-3 text-xs font-bold text-red-500 hover:text-red-400 rounded-lg hover:bg-red-500/10 flex items-center gap-1"
                                >
                                    <Trash2 className="w-3.5 h-3.5" />
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Floating Cart Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="relative w-14 h-14 rounded-full bg-blue-600 hover:bg-blue-500 text-white shadow-xl shadow-blue-500/30 flex items-center justify-center transition-all hover:scale-105 active:scale-95"
            >
                {isOpen ? (
                    <ChevronDown className="w-6 h-6" />
                ) : (
                    <ShoppingCart className="w-6 h-6" />
                )}
                {/* Count Badge */}
                {!isOpen && (
                    <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                        {items.length}
                    </span>
                )}
            </button>
        </div>
    );
}
