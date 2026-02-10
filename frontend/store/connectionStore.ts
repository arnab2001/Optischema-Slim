import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ConnectionState {
    isConnected: boolean;
    connectionString: string | null;
    connectionStatus: 'idle' | 'connecting' | 'connected' | 'error';
    errorMessage: string | null;

    setConnected: (connected: boolean) => void;
    setConnectionString: (connectionString: string) => void;
    setConnectionStatus: (status: 'idle' | 'connecting' | 'connected' | 'error') => void;
    setErrorMessage: (message: string | null) => void;
    syncStatus: () => Promise<void>;
    disconnect: () => void;
}

export const useConnectionStore = create<ConnectionState>()(
    persist(
        (set, get) => ({
            isConnected: false,
            connectionString: null,
            connectionStatus: 'idle',
            errorMessage: null,

            setConnected: (connected) => set({ isConnected: connected }),
            setConnectionString: (connectionString) => set({ connectionString }),
            setConnectionStatus: (status) => set({ connectionStatus: status }),
            setErrorMessage: (message) => set({ errorMessage: message }),

            syncStatus: async () => {
                try {
                    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
                    const res = await fetch(`${apiUrl}/api/connection/status`);
                    if (res.ok) {
                        const data = await res.json();
                        if (data.connected) {
                            set({
                                isConnected: true,
                                connectionStatus: 'connected',
                                // If backend has a connection string, update it if not set
                                connectionString: get().connectionString || data.current_config?.connection_string || null
                            });
                        } else {
                            set({ isConnected: false, connectionStatus: 'idle' });
                        }
                    }
                } catch (e) {
                    console.error("Failed to sync connection status:", e);
                }
            },

            disconnect: () => set({
                isConnected: false,
                connectionString: null,
                connectionStatus: 'idle',
                errorMessage: null
            }),
        }),
        {
            name: 'optischema-connection-storage',
            partialize: (state) => ({
                // Only persist connection string if needed, but maybe safer not to?
                // Let's persist it for convenience as requested in "Slim" vision (local-first)
                connectionString: state.connectionString,
                isConnected: state.isConnected
            }),
        }
    )
);
