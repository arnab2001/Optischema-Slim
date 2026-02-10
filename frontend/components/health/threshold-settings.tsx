"use client";

import { useState, useEffect } from "react";
import { useAppStore } from "@/store/appStore";
import { Settings, Shield, Activity, HardDrive, Search, Save, Loader2, Info } from "lucide-react";
import { toast } from "sonner";

interface HealthThresholds {
    bloat_min_size_mb: number;
    bloat_min_ratio_percent: number;
    index_unused_min_size_mb: number;
    query_slow_ms: number;
    query_high_impact_percent: number;
}

export function ThresholdSettings() {
    const { theme } = useAppStore();
    const isDark = theme === "dark";
    const [config, setConfig] = useState<HealthThresholds>({
        bloat_min_size_mb: 100,
        bloat_min_ratio_percent: 20,
        index_unused_min_size_mb: 10,
        query_slow_ms: 100,
        query_high_impact_percent: 20
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";

    useEffect(() => {
        fetchThresholds();
    }, []);

    const fetchThresholds = async () => {
        try {
            const res = await fetch(`${apiUrl}/api/health-thresholds`);
            if (res.ok) {
                const data = await res.json();
                setConfig(data);
            }
        } catch (e) {
            console.error("Failed to fetch thresholds:", e);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            const res = await fetch(`${apiUrl}/api/health-thresholds`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(config),
            });
            if (res.ok) {
                toast.success("Health thresholds updated");
            } else {
                toast.error("Failed to update thresholds");
            }
        } catch (e) {
            toast.error("An error occurred while saving");
        } finally {
            setSaving(false);
        }
    };

    const Label = ({ children }: { children: React.ReactNode }) => (
        <label className={`block text-xs font-bold uppercase tracking-wider mb-1.5 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
            {children}
        </label>
    );

    const Input = ({ value, onChange, unit }: { value: number; onChange: (v: number) => void; unit: string }) => (
        <div className="relative flex items-center">
            <input
                type="number"
                value={value}
                onChange={(e) => onChange(parseInt(e.target.value) || 0)}
                className={`w-full px-3 py-2 rounded-lg border font-mono text-sm ${isDark
                    ? "bg-slate-800 border-slate-700 text-white"
                    : "bg-white border-slate-200 text-slate-800"
                    } focus:ring-2 focus:ring-blue-500 outline-none`}
            />
            <span className={`absolute right-3 text-[10px] font-bold uppercase ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                {unit}
            </span>
        </div>
    );

    const Slider = ({ value, onChange, min = 0, max = 100 }: { value: number; onChange: (v: number) => void; min?: number; max?: number }) => (
        <div className="space-y-2">
            <input
                type="range"
                min={min}
                max={max}
                value={value}
                onChange={(e) => onChange(parseInt(e.target.value))}
                className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
            <div className="flex justify-between text-[10px] font-mono text-slate-500">
                <span>{min}%</span>
                <span className="text-blue-400 font-bold">{value}%</span>
                <span>{max}%</span>
            </div>
        </div>
    );

    if (loading) return null;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h2 className={`text-lg font-semibold flex items-center gap-2 ${isDark ? "text-white" : "text-slate-800"}`}>
                    <Activity className="w-5 h-5 text-blue-500" />
                    Health Thresholds
                </h2>
                <div className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-widest ${isDark ? "bg-slate-800 text-slate-400" : "bg-slate-100 text-slate-500"}`}>
                    Diagnostic Profile
                </div>
            </div>

            {/* Storage Section */}
            <div className={`p-5 rounded-xl border space-y-6 ${isDark ? "bg-slate-900/50 border-slate-800" : "bg-white border-slate-200"}`}>
                <div className="flex items-center gap-2 border-b pb-3 border-slate-800">
                    <HardDrive className="w-4 h-4 text-slate-500" />
                    <span className="text-xs font-bold uppercase tracking-widest text-slate-400">Storage & Bloat</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <Label>Min Table Size to Alert</Label>
                        <Input
                            value={config.bloat_min_size_mb}
                            onChange={(v) => setConfig({ ...config, bloat_min_size_mb: v })}
                            unit="MB"
                        />
                        <p className="text-[10px] text-slate-500 leading-relaxed italic">
                            Ignore bloat on small tables. Recommended: 100MB+ for production.
                        </p>
                    </div>

                    <div className="space-y-4">
                        <Label>Min Bloat Ratio</Label>
                        <Slider
                            value={config.bloat_min_ratio_percent}
                            onChange={(v) => setConfig({ ...config, bloat_min_ratio_percent: v })}
                        />
                        <p className="text-[10px] text-slate-500 leading-relaxed italic">
                            Alert when dead tuples exceed this percentage of total tuples.
                        </p>
                    </div>
                </div>

                <div className="pt-2">
                    <Label>Min Unused Index Size</Label>
                    <div className="flex gap-4 items-center">
                        <div className="w-32">
                            <Input
                                value={config.index_unused_min_size_mb}
                                onChange={(v) => setConfig({ ...config, index_unused_min_size_mb: v })}
                                unit="MB"
                            />
                        </div>
                        <p className="text-[10px] text-slate-500 flex-1 italic">
                            Don't flag indexes smaller than this (e.g., PKs on empty tables).
                        </p>
                    </div>
                </div>
            </div>

            {/* Performance Section */}
            <div className={`p-5 rounded-xl border space-y-6 ${isDark ? "bg-slate-900/50 border-slate-800" : "bg-white border-slate-200"}`}>
                <div className="flex items-center gap-2 border-b pb-3 border-slate-800">
                    <Search className="w-4 h-4 text-slate-500" />
                    <span className="text-xs font-bold uppercase tracking-widest text-slate-400">Query Performance</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <Label>Slow Query Threshold</Label>
                        <Input
                            value={config.query_slow_ms}
                            onChange={(v) => setConfig({ ...config, query_slow_ms: v })}
                            unit="MS"
                        />
                        <p className="text-[10px] text-slate-500 leading-relaxed italic">
                            Queries taking longer than this are flagged as "Slow".
                        </p>
                    </div>

                    <div className="space-y-4">
                        <Label>High Impact Threshold</Label>
                        <Slider
                            value={config.query_high_impact_percent}
                            onChange={(v) => setConfig({ ...config, query_high_impact_percent: v })}
                        />
                        <p className="text-[10px] text-slate-500 leading-relaxed italic">
                            Flag queries consuming more than this % of total DB execution time.
                        </p>
                    </div>
                </div>
            </div>

            {/* Context Note */}
            <div className={`p-4 rounded-lg flex gap-3 ${isDark ? "bg-blue-500/5 border border-blue-500/10" : "bg-blue-50 border border-blue-100"}`}>
                <Info className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                <p className={`text-[11px] leading-relaxed ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                    <span className="font-bold">Pro-tip:</span> These thresholds only affect the <span className="text-blue-500 font-bold">Health Doctor</span> scan results. Real-time metrics on the main dashboard will still show all raw data, but the health score and automated triage will follow these "Profile" rules.
                </p>
            </div>

            <button
                onClick={handleSave}
                disabled={saving}
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold flex items-center justify-center gap-2 disabled:opacity-50 transition-all shadow-lg shadow-blue-500/20 active:scale-[0.98]"
            >
                {saving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                    <Save className="w-4 h-4" />
                )}
                Save Diagnostic Profile
            </button>
        </div>
    );
}
