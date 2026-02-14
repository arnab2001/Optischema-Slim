"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface CartItem {
    id: string;
    type: "index" | "rewrite" | "drop";
    sql: string;
    description: string;
    table: string;
    estimatedImprovement?: number;
    source: "analysis" | "index-advisor" | "health";
}

interface CartState {
    items: CartItem[];
    addItem: (item: CartItem) => void;
    removeItem: (id: string) => void;
    clearCart: () => void;
    isInCart: (sql: string) => boolean;
    totalEstimatedImprovement: () => number;
}

export const useCartStore = create<CartState>()(
    persist(
        (set, get) => ({
            items: [],

            addItem: (item) =>
                set((state) => {
                    // Deduplicate by SQL content
                    const normalized = item.sql.trim().toLowerCase();
                    if (state.items.some((i) => i.sql.trim().toLowerCase() === normalized)) {
                        return state;
                    }
                    return { items: [...state.items, item] };
                }),

            removeItem: (id) =>
                set((state) => ({
                    items: state.items.filter((i) => i.id !== id),
                })),

            clearCart: () => set({ items: [] }),

            isInCart: (sql) => {
                const normalized = sql.trim().toLowerCase();
                return get().items.some((i) => i.sql.trim().toLowerCase() === normalized);
            },

            totalEstimatedImprovement: () => {
                const items = get().items;
                if (items.length === 0) return 0;
                return items.reduce((sum, i) => sum + (i.estimatedImprovement || 0), 0);
            },
        }),
        {
            name: "optischema-cart-store",
        }
    )
);
