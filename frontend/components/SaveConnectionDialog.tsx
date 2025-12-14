"use client";

import { useState } from "react";
import { Database, X } from "lucide-react";

interface SaveConnectionDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (name: string) => Promise<void>;
    connectionDetails: {
        host: string;
        port: string;
        database: string;
        username: string;
    } | null;
}

export function SaveConnectionDialog({
    isOpen,
    onClose,
    onSave,
    connectionDetails
}: SaveConnectionDialogProps) {
    const [name, setName] = useState("");
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Reset state when dialog opens/closes
    const handleClose = () => {
        setName("");
        setError(null);
        setSaving(false);
        onClose();
    };

    if (!isOpen) return null;

    const handleSave = async () => {
        if (!name.trim()) {
            setError("Connection name is required");
            return;
        }

        setSaving(true);
        setError(null);
        try {
            await onSave(name.trim());
            setName("");
            handleClose();
        } catch (err: any) {
            // Check for duplicate credentials error
            const errorMsg = err.message || "Failed to save connection";
            if (errorMsg.includes("already exists as")) {
                setError(`⚠️ ${errorMsg} You can use that saved connection instead.`);
            } else if (errorMsg.includes("already exists")) {
                setError(`⚠️ ${errorMsg}`);
            } else {
                setError(errorMsg);
            }
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
                <div className="flex items-center justify-between p-4 border-b">
                    <div className="flex items-center gap-2">
                        <Database className="w-5 h-5 text-blue-600" />
                        <h2 className="text-lg font-semibold text-gray-900">Save Connection</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="p-4 space-y-4">
                    {connectionDetails && (
                        <div className="bg-gray-50 rounded-lg p-3 space-y-1 text-sm">
                            <div><strong>Host:</strong> {connectionDetails.host}:{connectionDetails.port}</div>
                            <div><strong>Database:</strong> {connectionDetails.database}</div>
                            <div><strong>User:</strong> {connectionDetails.username}</div>
                        </div>
                    )}

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Connection Name
                        </label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="e.g., Production DB, Staging Server"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                            autoFocus
                            onKeyDown={(e) => {
                                if (e.key === "Enter" && !saving) {
                                    handleSave();
                                }
                            }}
                        />
                    </div>

                    {error && (
                        <div className="bg-red-50 text-red-600 text-sm p-3 rounded-lg">
                            {error}
                        </div>
                    )}
                </div>

                <div className="flex items-center justify-end gap-2 p-4 border-t">
                    <button
                        onClick={handleClose}
                        disabled={saving}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving || !name.trim()}
                        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {saving ? "Saving..." : "Save"}
                    </button>
                </div>
            </div>
        </div>
    );
}

