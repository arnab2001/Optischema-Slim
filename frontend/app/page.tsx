import { useConnectionStore } from "@/store/connectionStore";
import { ConnectionWizard } from "@/components/connection-wizard";
import { ExtensionCheck } from "@/components/extension-check";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function Home() {
  const { isConnected, connectionString, disconnect, syncStatus } = useConnectionStore();
  const navigate = useNavigate();
  const [step, setStep] = useState<"connect" | "check">("connect");

  // Check backend connection status on mount (e.g. for Quickstart Demo)
  useEffect(() => {
    syncStatus();
  }, [syncStatus]);

  // If already connected with a saved connection string, skip to extension check
  useEffect(() => {
    if (isConnected && connectionString) {
      setStep("check");
    } else {
      setStep("connect");
    }
  }, [isConnected, connectionString]);

  const handleConnected = () => {
    setStep("check");
  };

  const handleCheckComplete = () => {
    navigate("/dashboard");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex flex-col justify-center py-12 px-4">
      <div className="max-w-md mx-auto w-full">
        {/* Branding */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-blue-500/25">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
            OptiSchema<span className="text-blue-600">Slim</span>
          </h1>
          <p className="mt-2 text-slate-500">
            AI-powered PostgreSQL optimization
          </p>
        </div>

        {/* Connection Flow */}
        {step === "connect" && <ConnectionWizard onConnect={handleConnected} />}
        {step === "check" && (
          <ExtensionCheck
            onComplete={handleCheckComplete}
            onBack={() => {
              disconnect();
              setStep("connect");
            }}
          />
        )}

        {/* Footer */}
        <p className="text-center text-xs text-slate-400 mt-8">
          Your data stays local. Privacy-first by design.
        </p>
      </div>
    </div>
  );
}
