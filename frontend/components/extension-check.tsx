"use client";

import { useState, useEffect } from "react";
import { CheckCircle2, AlertTriangle, Loader2, ArrowRight, Database } from "lucide-react";

interface ExtensionCheckProps {
    onComplete: () => void;
    onBack?: () => void;
}

interface ExtensionStatus {
    pgstat: boolean;
    hypopg: boolean;
}

export function ExtensionCheck({ onComplete, onBack }: ExtensionCheckProps) {
    const [checking, setChecking] = useState(true);
    const [status, setStatus] = useState<ExtensionStatus>({ pgstat: false, hypopg: false });
    const [enabling, setEnabling] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

    const checkExtensions = async () => {
        setChecking(true);
        try {
            const [pgstatRes, hypopgRes] = await Promise.all([
                fetch(`${apiUrl}/api/connection/extension/check`),
                fetch(`${apiUrl}/api/connection/extension/hypopg/check`)
            ]);

            const pgstatData = await pgstatRes.json();
            const hypopgData = await hypopgRes.json();

            setStatus({
                pgstat: pgstatData.enabled || false,
                hypopg: hypopgData.enabled || false
            });
        } catch (e: any) {
            console.error("Failed to check extensions:", e);
            setError(`Failed to verify extension status: ${e.message}`);
        } finally {
            setChecking(false);
        }
    };

    useEffect(() => {
        checkExtensions();
    }, []);

    const handleEnable = async (ext: "pgstat" | "hypopg") => {
        setEnabling(ext);
        setError(null);
        try {
            const endpoint = ext === "pgstat"
                ? `${apiUrl}/api/connection/extension/enable`
                : `${apiUrl}/api/connection/extension/hypopg/enable`;

            const res = await fetch(endpoint, { method: "POST" });
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || `Failed to enable ${ext}`);
            }

            setStatus(prev => ({ ...prev, [ext]: true }));
        } catch (err: any) {
            setError(err.message);
        } finally {
            setEnabling(null);
        }
    };

    if (checking) {
        return (
            <div className="w-full max-w-md mx-auto bg-white rounded-xl shadow-lg border border-slate-200 p-8 text-center">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-slate-800">Verifying Database Setup...</h3>
                <p className="text-slate-500 mt-2">Checking for required extensions.</p>
            </div>
        );
    }

    const allEnabled = status.pgstat && status.hypopg;
    const pgstatOnly = status.pgstat && !status.hypopg;

    if (allEnabled) {
        return (
            <div className="w-full max-w-md mx-auto bg-white rounded-xl shadow-lg border border-slate-200 p-8 text-center">
                <div className="w-12 h-12 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle2 className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold text-slate-800">Ready to Optimize!</h3>
                <p className="text-slate-500 mt-2 mb-4">
                    All extensions are active.
                </p>
                <div className="flex gap-2 justify-center mb-6">
                    <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-medium">pg_stat_statements ✓</span>
                    <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-medium">HypoPG ✓</span>
                </div>
                <button
                    onClick={onComplete}
                    className="w-full py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center justify-center gap-2"
                >
                    Go to Dashboard
                    <ArrowRight className="w-4 h-4" />
                </button>
                {onBack && (
                    <button
                        onClick={onBack}
                        className="w-full py-2.5 mt-3 bg-white text-slate-600 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors font-medium"
                    >
                        Use a different connection
                    </button>
                )}
            </div>
        );
    }

    return (
        <div className="w-full max-w-md mx-auto bg-white rounded-xl shadow-lg border border-slate-200 p-8">
            <div className="text-center mb-6">
                <div className="w-12 h-12 bg-yellow-100 text-yellow-600 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Database className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold text-slate-800">Extensions Required</h3>
                <p className="text-slate-500 mt-2">
                    OptiSchema works best with these PostgreSQL extensions.
                </p>
            </div>

            {/* Extension Status Cards */}
            <div className="space-y-3 mb-6">
                {/* pg_stat_statements */}
                <div className={`p-4 rounded-lg border ${status.pgstat ? 'bg-green-50 border-green-200' : 'bg-slate-50 border-slate-200'}`}>
                    <div className="flex items-center justify-between">
                        <div>
                            <p className={`font-medium ${status.pgstat ? 'text-green-800' : 'text-slate-800'}`}>
                                pg_stat_statements
                            </p>
                            <p className="text-xs text-slate-500">Query performance tracking</p>
                        </div>
                        {status.pgstat ? (
                            <CheckCircle2 className="w-5 h-5 text-green-600" />
                        ) : (
                            <button
                                onClick={() => handleEnable("pgstat")}
                                disabled={enabling === "pgstat"}
                                className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
                            >
                                {enabling === "pgstat" ? <Loader2 className="w-4 h-4 animate-spin" /> : "Enable"}
                            </button>
                        )}
                    </div>
                </div>

                {/* HypoPG */}
                <div className={`p-4 rounded-lg border ${status.hypopg ? 'bg-green-50 border-green-200' : 'bg-slate-50 border-slate-200'}`}>
                    <div className="flex items-center justify-between">
                        <div>
                            <p className={`font-medium ${status.hypopg ? 'text-green-800' : 'text-slate-800'}`}>
                                HypoPG
                            </p>
                            <p className="text-xs text-slate-500">Index impact simulation</p>
                        </div>
                        {status.hypopg ? (
                            <CheckCircle2 className="w-5 h-5 text-green-600" />
                        ) : (
                            <button
                                onClick={() => handleEnable("hypopg")}
                                disabled={enabling === "hypopg"}
                                className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
                            >
                                {enabling === "hypopg" ? <Loader2 className="w-4 h-4 animate-spin" /> : "Enable"}
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {error && (
                <div className="p-3 bg-red-50 text-red-600 text-sm rounded mb-4">
                    {error}
                </div>
            )}

            <div className="space-y-3">
                {pgstatOnly && (
                    <button
                        onClick={onComplete}
                        className="w-full py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center justify-center gap-2"
                    >
                        Continue Without HypoPG
                        <ArrowRight className="w-4 h-4" />
                    </button>
                )}
                <button
                    onClick={checkExtensions}
                    className="w-full py-2.5 bg-white text-slate-600 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors font-medium"
                >
                    Check Again
                </button>
                {onBack && (
                    <button
                        onClick={onBack}
                        className="w-full py-2.5 bg-white text-slate-600 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors font-medium"
                    >
                        Enter new database credentials
                    </button>
                )}
            </div>
        </div>
    );
}
