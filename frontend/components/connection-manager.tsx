"use client";

import type * as React from "react";
import { useState, useEffect } from "react";
import { useConnectionStore } from "@/store/connectionStore";
import { AlertCircle, CheckCircle2, Database, Loader2 } from "lucide-react";

export function ConnectionManager() {
    const {
        isConnected,
        connectionString,
        connectionStatus,
        errorMessage,
        setConnected,
        setConnectionString,
        setConnectionStatus,
        setErrorMessage,
        disconnect
    } = useConnectionStore();

    const [inputString, setInputString] = useState("");
    const apiUrl = import.meta.env.VITE_API_URL || "";

    const normalizeConnectionString = (raw: string) => {
        const trimmed = raw.trim();
        if (!trimmed) return trimmed;
        return /^postgres(ql)?:\/\//i.test(trimmed) ? trimmed : `postgresql://${trimmed}`;
    };

    // Initialize input from store on mount
    useEffect(() => {
        if (connectionString) {
            setInputString(connectionString);
        }
    }, [connectionString]);

    // Check connection status on mount
    useEffect(() => {
        const checkStatus = async () => {
            try {
                const res = await fetch(`${apiUrl}/api/connection/status`);
                const data = await res.json();
                if (data.connected) {
                    setConnected(true);
                    setConnectionStatus("connected");
                    // Fetch active config if needed, but for now just trust the status
                } else {
                    setConnected(false);
                    setConnectionStatus("idle");
                }
            } catch (e) {
                console.error("Failed to check status:", e);
            }
        };
        checkStatus();
    }, [setConnected, setConnectionStatus]);

    const handleConnect = async (e: React.FormEvent) => {
        e.preventDefault();
        setConnectionStatus("connecting");
        setErrorMessage(null);

        const finalConnectionString = normalizeConnectionString(inputString);

        try {
            const res = await fetch(`${apiUrl}/api/connection/connect`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ connection_string: finalConnectionString }),
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || "Failed to connect");
            }

            setConnected(true);
            setConnectionString(finalConnectionString);
            setConnectionStatus("connected");
        } catch (err: any) {
            setConnected(false);
            setConnectionStatus("error");
            setErrorMessage(err.message);
        }
    };

    const handleDisconnect = async () => {
        try {
            await fetch(`${apiUrl}/api/connection/disconnect`, { method: "POST" });
            disconnect();
            setInputString("");
        } catch (e) {
            console.error("Disconnect failed:", e);
        }
    };

    return (
        <div className="p-6 bg-white rounded-lg shadow-sm border border-slate-200">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                    <Database className="w-5 h-5 text-slate-500" />
                    Database Connection
                </h2>
                {connectionStatus === "connected" && (
                    <span className="flex items-center gap-1 text-sm text-green-600 bg-green-50 px-2 py-1 rounded-full">
                        <CheckCircle2 className="w-4 h-4" />
                        Connected
                    </span>
                )}
            </div>

            {connectionStatus === "connected" ? (
                <div className="space-y-4">
                    <div className="p-3 bg-slate-50 rounded text-sm font-mono text-slate-600 break-all">
                        {connectionString?.replace(/:[^:]*@/, ":****@")} {/* Mask password */}
                    </div>
                    <button
                        onClick={handleDisconnect}
                        className="w-full py-2 px-4 bg-red-50 text-red-600 rounded hover:bg-red-100 transition-colors text-sm font-medium"
                    >
                        Disconnect
                    </button>
                </div>
            ) : (
                <form onSubmit={handleConnect} className="space-y-4">
                    <div>
                        <label htmlFor="conn-string" className="block text-sm font-medium text-slate-700 mb-1">
                            Connection String
                        </label>
                        <input
                            id="conn-string"
                            type="text"
                            value={inputString}
                            onChange={(e) => setInputString(e.target.value)}
                            placeholder="postgresql://user:pass@localhost:5432/dbname"
                            className="w-full p-2 border border-slate-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm font-mono"
                            required
                        />
                    </div>

                    {errorMessage && (
                        <div className="p-3 bg-red-50 text-red-600 text-sm rounded flex items-start gap-2">
                            <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                            <span>{errorMessage}</span>
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={connectionStatus === "connecting"}
                        className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                        {connectionStatus === "connecting" ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Connecting...
                            </>
                        ) : (
                            "Connect"
                        )}
                    </button>
                </form>
            )}
        </div>
    );
}
