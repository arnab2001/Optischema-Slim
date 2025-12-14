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
    disconnect: () => void;
}

export const useConnectionStore = create<ConnectionState>()(
    persist(
        (set) => ({
            isConnected: false,
            connectionString: null,
            connectionStatus: 'idle',
            errorMessage: null,

            setConnected: (connected) => set({ isConnected: connected }),
            setConnectionString: (connectionString) => set({ connectionString }),
            setConnectionStatus: (status) => set({ connectionStatus: status }),
            setErrorMessage: (message) => set({ errorMessage: message }),
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
