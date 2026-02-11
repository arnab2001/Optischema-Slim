"use client";

import { useAppStore } from "@/store/appStore";
import { useConnectionStore } from "@/store/connectionStore";
import {
    LayoutDashboard,
    BarChart3,
    Bookmark,
    Settings,
    ChevronLeft,
    ChevronRight,
    Database,
    ChevronDown,
    Plus,
    Check,
    Star,
    RefreshCw
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useState, useEffect } from "react";

interface SavedConnection {
    id: number;
    name: string;
    host: string;
    port: string;
    database: string;
    username: string;
    ssl: boolean;
    last_used_at: string | null;
}

const navItems = [
    { href: "/dashboard", label: "Monitor", icon: LayoutDashboard },
    { href: "/health", label: "Health", icon: BarChart3 },
    { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
    const { isSidebarCollapsed, toggleSidebar, theme } = useAppStore();
    const { isConnected, connectionString, syncStatus } = useConnectionStore();
    const { pathname } = useLocation();
    const [connectionDropdownOpen, setConnectionDropdownOpen] = useState(false);
    const [savedConnections, setSavedConnections] = useState<SavedConnection[]>([]);
    const [activeConnectionId, setActiveConnectionId] = useState<number | null>(null);
    const [activeConnectionName, setActiveConnectionName] = useState<string | null>(null);
    const [switching, setSwitching] = useState(false);
    const [aiReady, setAiReady] = useState(true); // Default true to avoid flash

    const isDark = theme === "dark";

    // Fetch saved connections and current status
    const fetchConnections = async () => {
        const apiUrl = import.meta.env.VITE_API_URL || "";
        try {
            // Sync with global store
            await syncStatus();

            const savedRes = await fetch(`${apiUrl}/api/connection/saved`);
            if (savedRes.ok) {
                const data = await savedRes.json();
                setSavedConnections(data.connections || []);
            }

            const statusRes = await fetch(`${apiUrl}/api/connection/status`);
            if (statusRes.ok) {
                const status = await statusRes.json();
                setActiveConnectionId(status.saved_connection_id);

                // Find the name of the active connection
                if (status.saved_connection_id) {
                    const activeConn = savedConnections.find(c => c.id === status.saved_connection_id);
                    setActiveConnectionName(activeConn?.name || null);
                } else {
                    setActiveConnectionName(null);
                }
            }

            // Check AI Status for sidebar warning
            const healthRes = await fetch(`${apiUrl}/api/health/check`);
            if (healthRes.ok) {
                const health = await healthRes.json();
                // If openai field (ai_healthy) is false, show warning
                setAiReady(health.openai);
            }
        } catch (error) {
            console.error("Failed to fetch connections:", error);
        }
    };

    useEffect(() => {
        fetchConnections();
    }, []);

    useEffect(() => {
        if (connectionDropdownOpen) {
            fetchConnections();
        }
    }, [connectionDropdownOpen]);

    // Update active connection name when savedConnections changes
    useEffect(() => {
        if (activeConnectionId) {
            const activeConn = savedConnections.find(c => c.id === activeConnectionId);
            setActiveConnectionName(activeConn?.name || null);
        }
    }, [savedConnections, activeConnectionId]);

    const handleSwitchConnection = async (connectionId: number) => {
        if (switching || connectionId === activeConnectionId) return;

        setSwitching(true);
        const apiUrl = import.meta.env.VITE_API_URL || "";
        try {
            const response = await fetch(`${apiUrl}/api/connection/switch/${connectionId}`, {
                method: 'POST'
            });

            if (response.ok) {
                await fetchConnections();
                setConnectionDropdownOpen(false);
                window.location.reload();
            } else {
                const error = await response.json().catch(() => ({}));
                alert(error.detail || 'Failed to switch connection');
            }
        } catch (error) {
            console.error('Failed to switch connection:', error);
            alert('Failed to switch connection');
        } finally {
            setSwitching(false);
        }
    };

    // Display name: prefer saved connection name, fallback to masked connection string
    const displayName = activeConnectionName || (connectionString
        ? connectionString.replace(/:[^:@]+@/, ":****@").substring(0, 30) + "..."
        : "No connection");

    // Mask connection string for display
    const maskedConnection = connectionString
        ? connectionString.replace(/:[^:@]+@/, ":****@").substring(0, 35) + "..."
        : "No connection";

    return (
        <aside
            className={`fixed left-0 top-0 h-full z-30 transition-all duration-300 ${isSidebarCollapsed ? "w-16" : "w-64"
                } ${isDark ? "bg-slate-800 border-slate-700" : "bg-white border-slate-200"} border-r`}
        >
            <div className="flex flex-col h-full">
                {/* Logo / Brand */}
                <div className={`h-16 flex items-center px-4 border-b ${isDark ? "border-slate-700" : "border-slate-200"}`}>
                    {!isSidebarCollapsed && (
                        <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
                                <Database className="w-4 h-4 text-white" />
                            </div>
                            <span className={`font-bold text-lg ${isDark ? "text-white" : "text-slate-800"}`}>
                                OptiSchema
                            </span>
                        </div>
                    )}
                    {isSidebarCollapsed && (
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mx-auto">
                            <Database className="w-4 h-4 text-white" />
                        </div>
                    )}
                </div>

                {/* Connection Switcher */}
                <div className={`p-3 border-b ${isDark ? "border-slate-700" : "border-slate-200"}`}>
                    {!isSidebarCollapsed ? (
                        <button
                            onClick={() => setConnectionDropdownOpen(!connectionDropdownOpen)}
                            className={`w-full p-3 rounded-lg text-left transition-colors ${isDark
                                ? "bg-slate-700 hover:bg-slate-600"
                                : "bg-slate-50 hover:bg-slate-100"
                                }`}
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 min-w-0">
                                    <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-slate-400"}`} />
                                    <div className="min-w-0">
                                        {activeConnectionName ? (
                                            <>
                                                <span className={`text-xs font-semibold block truncate ${isDark ? "text-slate-200" : "text-slate-700"}`}>
                                                    {activeConnectionName}
                                                </span>
                                                <span className={`text-[10px] block truncate ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                                    {isConnected ? "Connected" : "Disconnected"}
                                                </span>
                                            </>
                                        ) : (
                                            <span className={`text-xs font-medium truncate ${isDark ? "text-slate-300" : "text-slate-600"}`}>
                                                {isConnected ? displayName : "Not Connected"}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <ChevronDown className={`w-4 h-4 shrink-0 ${isDark ? "text-slate-400" : "text-slate-500"} ${connectionDropdownOpen ? "rotate-180" : ""} transition-transform`} />
                            </div>
                        </button>
                    ) : (
                        <button
                            onClick={() => setConnectionDropdownOpen(!connectionDropdownOpen)}
                            className={`w-10 h-10 mx-auto flex items-center justify-center rounded-lg ${isDark ? "bg-slate-700" : "bg-slate-100"
                                }`}
                            title={activeConnectionName || maskedConnection}
                        >
                            <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-slate-400"}`} />
                        </button>
                    )}

                    {/* Connection Dropdown */}
                    {connectionDropdownOpen && !isSidebarCollapsed && (
                        <div className={`mt-2 rounded-lg border shadow-lg overflow-hidden ${isDark ? "bg-slate-700 border-slate-600" : "bg-white border-slate-200"
                            }`}>
                            {/* Saved Connections */}
                            {savedConnections.length > 0 && (
                                <div className={`py-1 border-b ${isDark ? "border-slate-600" : "border-slate-100"}`}>
                                    <div className={`px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider ${isDark ? "text-slate-400" : "text-slate-400"}`}>
                                        Saved Connections
                                    </div>
                                    {savedConnections.map((conn) => (
                                        <button
                                            key={conn.id}
                                            onClick={() => handleSwitchConnection(conn.id)}
                                            disabled={switching || conn.id === activeConnectionId}
                                            className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors ${conn.id === activeConnectionId
                                                ? isDark ? "bg-blue-600/20 text-blue-400" : "bg-blue-50 text-blue-600"
                                                : isDark ? "text-slate-300 hover:bg-slate-600" : "text-slate-600 hover:bg-slate-50"
                                                } ${switching ? "opacity-50 cursor-wait" : ""}`}
                                        >
                                            {conn.id === activeConnectionId ? (
                                                <Check className="w-4 h-4 shrink-0" />
                                            ) : (
                                                <Star className="w-4 h-4 shrink-0 text-yellow-500" />
                                            )}
                                            <div className="min-w-0 flex-1">
                                                <div className="font-medium truncate">{conn.name}</div>
                                                <div className={`text-[10px] truncate ${isDark ? "text-slate-400" : "text-slate-500"}`}>
                                                    {conn.host}/{conn.database}
                                                </div>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            )}

                            {/* Add New Connection */}
                            <Link
                                to="/"
                                className={`flex items-center gap-2 px-3 py-2.5 text-sm ${isDark ? "text-slate-300 hover:bg-slate-600" : "text-slate-600 hover:bg-slate-50"
                                    }`}
                                onClick={() => setConnectionDropdownOpen(false)}
                            >
                                <Plus className="w-4 h-4" />
                                <span>Add New Connection</span>
                            </Link>
                        </div>
                    )}
                </div>

                {/* Navigation */}
                <nav className="flex-1 p-3 space-y-1">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href;
                        const Icon = item.icon;

                        return (
                            <Link
                                key={item.href}
                                to={item.href}
                                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors relative ${isActive
                                    ? isDark
                                        ? "bg-blue-600 text-white"
                                        : "bg-blue-50 text-blue-600"
                                    : isDark
                                        ? "text-slate-400 hover:text-white hover:bg-slate-700"
                                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                                    }`}
                            >
                                <Icon className="w-5 h-5 shrink-0" />
                                {!isSidebarCollapsed && (
                                    <span className="text-sm font-medium">{item.label}</span>
                                )}
                                {/* Red Dot for Missing AI Config */}
                                {item.label === "Settings" && !aiReady && (
                                    <div className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full animate-pulse shadow-sm shadow-red-500/50" title="AI Provider Missing" />
                                )}
                            </Link>
                        );
                    })}
                </nav>

                {/* Collapse Toggle */}
                <div className={`p-3 border-t ${isDark ? "border-slate-700" : "border-slate-200"}`}>
                    <button
                        onClick={toggleSidebar}
                        className={`w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg transition-colors ${isDark
                            ? "text-slate-400 hover:text-white hover:bg-slate-700"
                            : "text-slate-500 hover:text-slate-700 hover:bg-slate-100"
                            }`}
                    >
                        {isSidebarCollapsed ? (
                            <ChevronRight className="w-5 h-5" />
                        ) : (
                            <>
                                <ChevronLeft className="w-5 h-5" />
                                <span className="text-sm">Collapse</span>
                            </>
                        )}
                    </button>
                </div>
            </div>
        </aside>
    );
}
