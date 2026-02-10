"use client";

import { AppShell } from "@/components/layout/app-shell";
import { useAppStore } from "@/store/appStore";
import { Settings as SettingsIcon, Bot, Palette, Shield, Check, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";
import { toast } from "sonner";

interface SettingsData {
    llm_provider: "ollama" | "openai" | "gemini" | "deepseek";
    ollama_base_url: string;
    ollama_model: string;
    openai_api_key: string;
    openai_model: string;
    gemini_api_key: string;
    deepseek_api_key: string;
    privacy_mode: boolean;
}

interface OllamaModelSelectProps {
    baseUrl: string;
    value: string;
    onChange: (value: string) => void;
}

function OllamaModelSelect({ baseUrl, value, onChange }: OllamaModelSelectProps) {
    const { theme } = useAppStore();
    const isDark = theme === "dark";
    const [models, setModels] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchModels = async () => {
            if (!baseUrl) return;
            setLoading(true);
            setError(null);
            try {
                // Ensure base URL doesn't have trailing slash for clean appending
                const cleanBase = baseUrl.replace(/\/$/, "");
                const res = await fetch(`${cleanBase}/api/tags`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.models && Array.isArray(data.models)) {
                        setModels(data.models.map((m: any) => m.name));
                    }
                }
            } catch (e) {
                // Silent fail/log for now as user might be typing URL
                console.warn("Failed to fetch Ollama models", e);
            } finally {
                setLoading(false);
            }
        };

        const timeout = setTimeout(fetchModels, 500); // Debounce
        return () => clearTimeout(timeout);
    }, [baseUrl]);

    return (
        <div className="relative">
            <input
                list="ollama-models"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder="Select or type model name (e.g., deepseek-r1:14b)"
                className={`w-full px-3 py-2 rounded-lg border text-sm ${isDark
                    ? "bg-slate-700 border-slate-600 text-white placeholder:text-slate-500"
                    : "bg-white border-slate-300 text-slate-800 placeholder:text-slate-400"
                    } focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none`}
            />
            <datalist id="ollama-models">
                {models.map((model) => (
                    <option key={model} value={model} />
                ))}
            </datalist>
            {loading && (
                <div className="absolute right-3 top-2.5">
                    <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
                </div>
            )}
        </div>
    );
}

import { ThresholdSettings } from "@/components/health/threshold-settings";

export default function SettingsPage() {
    const { theme, toggleTheme } = useAppStore();
    const isDark = theme === "dark";
    const [activeTab, setActiveTab] = useState<"general" | "thresholds">("general");

    const [settings, setSettings] = useState<SettingsData>({
        llm_provider: "ollama",
        ollama_base_url: "http://localhost:11434",
        ollama_model: "sqlcoder:7b",
        openai_api_key: "",
        openai_model: "gpt-4o-mini",
        gemini_api_key: "",
        deepseek_api_key: "",
        privacy_mode: false,
    });
    const [saving, setSaving] = useState(false);
    const [loading, setLoading] = useState(true);
    const [testing, setTesting] = useState(false);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";

    useEffect(() => {
        fetchSettings();
    }, []);

    const fetchSettings = async () => {
        try {
            const res = await fetch(`${apiUrl}/api/settings`);
            if (res.ok) {
                const data = await res.json();
                setSettings(prev => ({ ...prev, ...data }));
            }
        } catch (e) {
            console.error("Failed to fetch settings:", e);
        } finally {
            setLoading(false);
        }
    };

    const testConnection = async () => {
        setTesting(true);
        try {
            const res = await fetch(`${apiUrl}/api/settings/llm/test`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(settings),
            });
            const data = await res.json();
            if (data.success) {
                toast.success(data.message || "Connection successful!");
            } else {
                toast.error(data.message || "Connection failed");
            }
        } catch (e) {
            toast.error("Failed to test connection");
        } finally {
            setTesting(false);
        }
    };

    const saveSettings = async () => {
        setSaving(true);
        try {
            const res = await fetch(`${apiUrl}/api/settings`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(settings),
            });
            if (res.ok) {
                toast.success("Settings saved");
            } else {
                toast.error("Failed to save settings");
            }
        } catch (e) {
            toast.error("Failed to save settings");
        } finally {
            setSaving(false);
        }
    };

    const Section = ({ title, icon: Icon, children }: { title: string; icon: React.ElementType; children: React.ReactNode }) => (
        <div className={`p-6 rounded-xl border ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"}`}>
            <h2 className={`text-lg font-semibold mb-4 flex items-center gap-2 ${isDark ? "text-white" : "text-slate-800"}`}>
                <Icon className="w-5 h-5" />
                {title}
            </h2>
            {children}
        </div>
    );

    const Label = ({ children }: { children: React.ReactNode }) => (
        <label className={`block text-sm font-medium mb-1 ${isDark ? "text-slate-300" : "text-slate-700"}`}>
            {children}
        </label>
    );

    const Input = ({ value, onChange, type = "text", placeholder = "" }: {
        value: string;
        onChange: (v: string) => void;
        type?: string;
        placeholder?: string;
    }) => (
        <input
            type={type}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className={`w-full px-3 py-2 rounded-lg border text-sm ${isDark
                ? "bg-slate-700 border-slate-600 text-white placeholder:text-slate-500"
                : "bg-white border-slate-300 text-slate-800 placeholder:text-slate-400"
                } focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none`}
        />
    );

    if (loading) {
        return (
            <AppShell>
                <div className="flex justify-center py-12">
                    <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                </div>
            </AppShell>
        );
    }

    return (
        <AppShell>
            <div className="space-y-6 max-w-2xl">
                <div className="flex items-center justify-between">
                    <h1 className={`text-2xl font-bold ${isDark ? "text-white" : "text-slate-800"}`}>
                        <SettingsIcon className="inline-block w-6 h-6 mr-2 -mt-1" />
                        Settings
                    </h1>
                </div>

                {/* Tab Switcher */}
                <div className={`p-1 rounded-lg flex gap-1 ${isDark ? "bg-slate-800" : "bg-slate-100"}`}>
                    <button
                        onClick={() => setActiveTab("general")}
                        className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all ${activeTab === "general"
                            ? isDark ? "bg-slate-700 text-white shadow-sm" : "bg-white text-slate-800 shadow-sm"
                            : "text-slate-500 hover:text-slate-400"
                            }`}
                    >
                        General Configurations
                    </button>
                    <button
                        onClick={() => setActiveTab("thresholds")}
                        className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all ${activeTab === "thresholds"
                            ? isDark ? "bg-slate-700 text-white shadow-sm" : "bg-white text-slate-800 shadow-sm"
                            : "text-slate-500 hover:text-slate-400"
                            }`}
                    >
                        Health Thresholds
                    </button>
                </div>

                {activeTab === "general" ? (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                        {/* AI Provider */}
                        <Section title="AI Provider" icon={Bot}>
                            <div className="space-y-4">
                                <div>
                                    <Label>Provider</Label>
                                    <div className="flex gap-2 flex-wrap">
                                        {(["ollama", "openai", "gemini", "deepseek"] as const).map((p) => (
                                            <button
                                                key={p}
                                                onClick={() => setSettings({ ...settings, llm_provider: p })}
                                                className={`px-4 py-2 rounded-lg text-sm font-medium capitalize ${settings.llm_provider === p
                                                    ? "bg-blue-600 text-white"
                                                    : isDark
                                                        ? "bg-slate-700 text-slate-300 hover:bg-slate-600"
                                                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                                                    }`}
                                            >
                                                {p}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {settings.llm_provider === "ollama" && (
                                    <>
                                        <div>
                                            <Label>Base URL</Label>
                                            <Input
                                                value={settings.ollama_base_url}
                                                onChange={(v) => setSettings({ ...settings, ollama_base_url: v })}
                                                placeholder="http://localhost:11434"
                                            />
                                        </div>
                                        <div>
                                            <Label>Model</Label>
                                            <OllamaModelSelect
                                                baseUrl={settings.ollama_base_url}
                                                value={settings.ollama_model}
                                                onChange={(v) => setSettings({ ...settings, ollama_model: v })}
                                            />
                                        </div>
                                    </>
                                )}

                                {settings.llm_provider === "openai" && (
                                    <>
                                        <div>
                                            <Label>API Key</Label>
                                            <Input
                                                type="password"
                                                value={settings.openai_api_key}
                                                onChange={(v) => setSettings({ ...settings, openai_api_key: v })}
                                                placeholder="sk-..."
                                            />
                                        </div>
                                        <div>
                                            <Label>Model</Label>
                                            <Input
                                                value={settings.openai_model}
                                                onChange={(v) => setSettings({ ...settings, openai_model: v })}
                                                placeholder="gpt-4o-mini"
                                            />
                                        </div>
                                    </>
                                )}

                                {settings.llm_provider === "gemini" && (
                                    <div>
                                        <Label>API Key</Label>
                                        <Input
                                            type="password"
                                            value={settings.gemini_api_key}
                                            onChange={(v) => setSettings({ ...settings, gemini_api_key: v })}
                                            placeholder="Your Gemini API Key"
                                        />
                                    </div>
                                )}

                                {settings.llm_provider === "deepseek" && (
                                    <div>
                                        <Label>API Key</Label>
                                        <Input
                                            type="password"
                                            value={settings.deepseek_api_key}
                                            onChange={(v) => setSettings({ ...settings, deepseek_api_key: v })}
                                            placeholder="Your DeepSeek API Key"
                                        />
                                    </div>
                                )}

                                <div className="pt-2">
                                    <button
                                        onClick={testConnection}
                                        disabled={testing}
                                        className={`w-full py-2 rounded-lg text-sm font-medium border flex items-center justify-center gap-2 transition-colors ${isDark
                                            ? "border-slate-600 text-slate-300 hover:bg-slate-700 hover:border-slate-500"
                                            : "border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300"
                                            } disabled:opacity-50`}
                                    >
                                        {testing ? (
                                            <>
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                                Testing...
                                            </>
                                        ) : (
                                            <>
                                                <Bot className="w-4 h-4" />
                                                Test Connection
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>
                        </Section>

                        {/* Appearance */}
                        <Section title="Appearance" icon={Palette}>
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className={isDark ? "text-white" : "text-slate-800"}>Dark Mode</p>
                                    <p className={`text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                        Toggle between light and dark theme
                                    </p>
                                </div>
                                <button
                                    onClick={toggleTheme}
                                    className={`w-12 h-6 rounded-full p-1 transition-colors ${isDark ? "bg-blue-600" : "bg-slate-300"
                                        }`}
                                >
                                    <div className={`w-4 h-4 rounded-full bg-white transition-transform ${isDark ? "translate-x-6" : "translate-x-0"
                                        }`} />
                                </button>
                            </div>
                        </Section>

                        {/* Privacy */}
                        <Section title="Privacy" icon={Shield}>
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className={isDark ? "text-white" : "text-slate-800"}>Privacy Mode</p>
                                    <p className={`text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                        Mask PII (emails, names) before sending to AI
                                    </p>
                                </div>
                                <button
                                    onClick={() => setSettings({ ...settings, privacy_mode: !settings.privacy_mode })}
                                    className={`w-12 h-6 rounded-full p-1 transition-colors ${settings.privacy_mode ? "bg-blue-600" : "bg-slate-300"
                                        }`}
                                >
                                    <div className={`w-4 h-4 rounded-full bg-white transition-transform ${settings.privacy_mode ? "translate-x-6" : "translate-x-0"
                                        }`} />
                                </button>
                            </div>
                        </Section>

                        {/* Save Button */}
                        <button
                            onClick={saveSettings}
                            disabled={saving}
                            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                            {saving ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Saving...
                                </>
                            ) : (
                                <>
                                    <Check className="w-4 h-4" />
                                    Save Settings
                                </>
                            )}
                        </button>
                    </div>
                ) : (
                    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <ThresholdSettings />
                    </div>
                )}
            </div>
        </AppShell>
    );
}
