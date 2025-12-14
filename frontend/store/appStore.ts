"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AppState {
    // Sidebar
    isSidebarCollapsed: boolean;
    toggleSidebar: () => void;

    // Live mode
    isLiveMode: boolean;
    setLiveMode: (value: boolean) => void;

    // Last updated
    lastUpdated: Date | null;
    setLastUpdated: (date: Date) => void;

    // Theme
    theme: "light" | "dark";
    setTheme: (theme: "light" | "dark") => void;
    toggleTheme: () => void;

    // Selected query for inspector
    selectedQueryId: string | null;
    setSelectedQueryId: (id: string | null) => void;
}

export const useAppStore = create<AppState>()(
    persist(
        (set) => ({
            // Sidebar
            isSidebarCollapsed: false,
            toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),

            // Live mode
            isLiveMode: true,
            setLiveMode: (value) => set({ isLiveMode: value }),

            // Last updated
            lastUpdated: null,
            setLastUpdated: (date) => set({ lastUpdated: date }),

            // Theme
            theme: "light",
            setTheme: (theme) => set({ theme }),
            toggleTheme: () => set((state) => ({ theme: state.theme === "light" ? "dark" : "light" })),

            // Selected query
            selectedQueryId: null,
            setSelectedQueryId: (id) => set({ selectedQueryId: id }),
        }),
        {
            name: "optischema-app-store",
            partialize: (state) => ({
                isSidebarCollapsed: state.isSidebarCollapsed,
                theme: state.theme,
                isLiveMode: state.isLiveMode,
            }),
        }
    )
);
