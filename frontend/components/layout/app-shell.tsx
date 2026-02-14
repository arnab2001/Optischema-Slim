"use client";

import { ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { TopBar } from "./top-bar";
import { useAppStore } from "@/store/appStore";
import { Toaster } from "sonner";
import { OptimizationCart } from "@/components/optimization-cart";

interface AppShellProps {
    children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
    const { isSidebarCollapsed, theme } = useAppStore();

    return (
        <div className={`min-h-screen ${theme === "dark" ? "dark bg-slate-900" : "bg-slate-50"}`}>
            <Toaster position="top-right" richColors />

            <div className="flex h-screen overflow-hidden">
                {/* Sidebar */}
                <Sidebar />

                {/* Main Content */}
                <div className={`flex-1 flex flex-col transition-all duration-300 ${isSidebarCollapsed ? "ml-16" : "ml-64"
                    }`}>
                    {/* Top Bar */}
                    <TopBar />

                    {/* Page Content */}
                    <main className="flex-1 overflow-auto p-4">
                        {children}
                    </main>
                </div>
            </div>

            {/* Floating Optimization Cart */}
            <OptimizationCart />
        </div>
    );
}
