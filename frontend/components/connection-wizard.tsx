"use client";

import { useState, useEffect } from "react";
import { useConnectionStore } from "@/store/connectionStore";
import { Database, Shield, ShieldAlert, Loader2, AlertCircle, Star, Check } from "lucide-react";

interface ConnectionWizardProps {
  onConnect: () => void;
}

export function ConnectionWizard({ onConnect }: ConnectionWizardProps) {
  const { setConnected, setConnectionString, setConnectionStatus, setErrorMessage } = useConnectionStore();

  const [mode, setMode] = useState<"string" | "manual">("manual");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Manual Form State
  const [host, setHost] = useState("localhost");
  const [port, setPort] = useState("5432");
  const [database, setDatabase] = useState("postgres");
  const [user, setUser] = useState("postgres");
  const [password, setPassword] = useState("");
  const [ssl, setSsl] = useState(false);

  // Save connection options
  const [saveConnection, setSaveConnection] = useState(true);
  const [connectionName, setConnectionName] = useState("");
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveWarning, setSaveWarning] = useState<string | null>(null);

  // Auto-detect RDS and enable SSL
  const isRdsHost = host.trim().includes(".rds.amazonaws.com") || host.trim().includes(".rds.amazonaws.com.cn");

  // Auto-enable SSL for RDS hosts
  useEffect(() => {
    if (isRdsHost) {
      setSsl(true);
    }
  }, [host]);

  // Auto-generate connection name from host
  useEffect(() => {
    if (!connectionName || connectionName === "localhost" || connectionName.includes(".rds.")) {
      const hostPart = host.trim().split('.')[0];
      if (hostPart && hostPart !== 'localhost') {
        setConnectionName(hostPart);
      }
    }
  }, [host]);

  // String Form State
  const [connString, setConnString] = useState("");
  const normalizeConnectionString = (raw: string) => {
    const trimmed = raw.trim();
    if (!trimmed) return trimmed;
    return /^postgres(ql)?:\/\//i.test(trimmed) ? trimmed : `postgresql://${trimmed}`;
  };

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setErrorMessage(null);
    setConnectionStatus("connecting");

    let finalConnectionString = connString.trim();

    if (mode === "manual") {
      // Construct connection string
      // Format: postgresql://user:password@host:port/dbname?sslmode=require
      const encodedUser = encodeURIComponent(user);
      const encodedPass = encodeURIComponent(password);
      const encodedDb = encodeURIComponent(database);
      // Host should generally not be encoded, but ensure no whitespace
      const cleanHost = host.trim();
      const cleanPort = port.trim();

      // Build base connection string
      finalConnectionString = `postgresql://${encodedUser}:${encodedPass}@${cleanHost}:${cleanPort}/${encodedDb}`;

      // Add SSL mode if enabled or if RDS host (RDS requires SSL)
      const needsSsl = ssl || isRdsHost;
      if (needsSsl) {
        const separator = finalConnectionString.includes("?") ? "&" : "?";
        finalConnectionString += `${separator}sslmode=require`;
      }

      // Log the constructed string for debugging (without password)
      console.log("Constructed connection string:", finalConnectionString.replace(/:[^:]*@/, ":****@"));
    } else {
      // Normalize user-provided connection string
      finalConnectionString = normalizeConnectionString(finalConnectionString);
    }

    // Ensure scheme is present for both modes
    finalConnectionString = normalizeConnectionString(finalConnectionString);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
      const res = await fetch(`${apiUrl}/api/connection/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ connection_string: finalConnectionString }),
      });

      if (!res.ok) {
        let errorMessage = "Failed to connect";
        try {
          const data = await res.json();
          // Handle different error response formats
          errorMessage = data.detail || data.message || data.error || errorMessage;
          // If detail is an object (structured error), extract the message
          if (typeof errorMessage === "object" && errorMessage !== null) {
            errorMessage = (errorMessage as any).message || JSON.stringify(errorMessage);
          }
        } catch (e) {
          // If JSON parsing fails, use status text
          errorMessage = res.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const data = await res.json();

      setConnected(true);
      setConnectionString(finalConnectionString);
      setConnectionStatus("connected");

      // Save connection if checkbox is checked and name is provided
      if (saveConnection && connectionName.trim()) {
        try {
          // Extract connection details for saving
          let saveHost = host.trim();
          let savePort = port.trim();
          let saveDb = database;
          let saveUser = user;
          let savePass = password;
          let saveSsl = ssl || isRdsHost;

          // If using connection string mode, parse it
          if (mode === "string" && finalConnectionString) {
            try {
              const normalizedStr = finalConnectionString.replace(/^postgres:\/\//, 'postgresql://');
              const url = new URL(normalizedStr);
              saveHost = url.hostname || saveHost;
              savePort = url.port || '5432';
              saveUser = url.username ? decodeURIComponent(url.username) : saveUser;
              savePass = url.password ? decodeURIComponent(url.password) : savePass;
              saveDb = url.pathname ? url.pathname.replace(/^\//, '').split('?')[0] : saveDb;
              saveSsl = normalizedStr.includes('sslmode=require') || saveSsl;
            } catch (e) {
              console.warn('Could not parse connection string for saving:', e);
            }
          }

          const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
          const saveRes = await fetch(`${apiUrl}/api/connection/save`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              name: connectionName.trim(),
              host: saveHost,
              port: savePort,
              database: saveDb,
              username: saveUser,
              password: savePass,
              ssl: saveSsl
            }),
          });

          if (saveRes.ok) {
            setSaveSuccess(true);
            console.log(`Connection "${connectionName}" saved successfully`);
          } else {
            const saveError = await saveRes.json().catch(() => ({}));
            // Handle structured error responses
            let errorMsg = saveError.detail || 'Unknown error';
            if (typeof errorMsg === 'object' && errorMsg.message) {
              errorMsg = errorMsg.message;
            }

            // Show warning for duplicate connections
            if (errorMsg.includes('already exists')) {
              setSaveWarning(errorMsg);
            }
            console.warn('Could not save connection:', errorMsg);
          }
        } catch (saveErr) {
          console.warn('Error saving connection:', saveErr);
        }
      }

      onConnect();
    } catch (err: any) {
      console.error(err);
      setConnected(false);
      setConnectionStatus("error");
      setError(err.message);
      setErrorMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden">
      <div className="bg-slate-50 p-6 border-b border-slate-200 text-center">
        <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-3">
          <Database className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-slate-800">Connect to PostgreSQL</h2>
        <p className="text-sm text-slate-500 mt-1">Enter your database credentials to get started</p>
      </div>

      <div className="p-6">
        {/* Tabs */}
        <div className="flex p-1 bg-slate-100 rounded-lg mb-6">
          <button
            onClick={() => setMode("manual")}
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${mode === "manual" ? "bg-white text-blue-600 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
          >
            Manual Entry
          </button>
          <button
            onClick={() => setMode("string")}
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${mode === "string" ? "bg-white text-blue-600 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
          >
            Connection String
          </button>
        </div>

        <form onSubmit={handleConnect} className="space-y-4">
          {mode === "manual" ? (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">Host</label>
                  <input
                    type="text"
                    value={host}
                    onChange={(e) => setHost(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    placeholder="localhost"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">Port</label>
                  <input
                    type="text"
                    value={port}
                    onChange={(e) => setPort(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    placeholder="5432"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Database Name</label>
                <input
                  type="text"
                  value={database}
                  onChange={(e) => setDatabase(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="postgres"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">User</label>
                  <input
                    type="text"
                    value={user}
                    onChange={(e) => setUser(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    placeholder="postgres"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">Password</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between p-3 bg-slate-50 rounded border border-slate-200">
                <div className="flex items-center gap-2">
                  {ssl || isRdsHost ? <Shield className="w-4 h-4 text-green-600" /> : <ShieldAlert className="w-4 h-4 text-slate-400" />}
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-slate-700">Enable SSL</span>
                    {isRdsHost && !ssl && (
                      <span className="text-xs text-blue-600">Required for RDS</span>
                    )}
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={ssl || isRdsHost}
                    onChange={(e) => setSsl(e.target.checked)}
                    disabled={isRdsHost}
                    className="sr-only peer disabled:cursor-not-allowed"
                  />
                  <div className={`w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600 ${isRdsHost ? 'bg-blue-600' : ''}`}></div>
                </label>
              </div>
            </>
          ) : (
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Connection String</label>
              <textarea
                value={connString}
                onChange={(e) => setConnString(e.target.value)}
                className="w-full p-3 border border-slate-300 rounded text-sm font-mono focus:ring-2 focus:ring-blue-500 outline-none h-32 resize-none"
                placeholder="postgresql://user:password@localhost:5432/dbname"
                required
              />
            </div>
          )}

          {/* Save Connection Option */}
          <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Star className={`w-4 h-4 ${saveConnection ? 'text-slate-600 fill-slate-600' : 'text-slate-400'}`} />
                <span className="text-sm font-medium text-slate-700">Save this connection</span>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={saveConnection}
                  onChange={(e) => setSaveConnection(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-slate-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-slate-600"></div>
              </label>
            </div>
            {saveConnection && (
              <div className="mt-3">
                <label className="block text-xs font-semibold text-slate-500 mb-1">Connection Name</label>
                <input
                  type="text"
                  value={connectionName}
                  onChange={(e) => setConnectionName(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded text-sm focus:ring-2 focus:ring-slate-500 outline-none"
                  placeholder="e.g., Production DB, Staging, Local"
                />
                <p className="text-xs text-slate-500 mt-1">Give this connection a name to easily switch between databases later</p>
              </div>
            )}
          </div>

          {error && (
            <div className="p-3 bg-red-50 text-red-600 text-sm rounded flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {saveSuccess && (
            <div className="p-3 bg-green-50 text-green-600 text-sm rounded flex items-center gap-2">
              <Check className="w-4 h-4 shrink-0" />
              <span>Connection saved! You can switch to it anytime from the database menu.</span>
            </div>
          )}

          {saveWarning && (
            <div className="p-3 bg-yellow-50 text-yellow-700 text-sm rounded flex items-start gap-2 border border-yellow-200">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0 text-yellow-500" />
              <span>Connection successful but not saved: {saveWarning}</span>
            </div>
          )}

          {/* Read-Only Toggle */}
          <div className="flex items-center justify-between px-1">
            <div className="flex flex-col">
              <span className="text-sm font-medium text-slate-700">Read-Only Mode</span>
              <span className="text-xs text-slate-500">Prevent accidental writes (INSERT, UPDATE, DELETE)</span>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" />
              <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Connecting...
              </>
            ) : saveConnection && connectionName.trim() ? (
              <>
                <Star className="w-4 h-4" />
                Connect & Save
              </>
            ) : (
              "Connect to Database"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
