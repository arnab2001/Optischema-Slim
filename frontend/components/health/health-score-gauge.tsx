
"use client";

import { useAppStore } from "@/store/appStore";

interface HealthScoreGaugeProps {
    score: number;
    loading?: boolean;
    compact?: boolean;
}

export function HealthScoreGauge({ score, loading, compact = false }: HealthScoreGaugeProps) {
    const { theme } = useAppStore();
    const isDark = theme === "dark";

    // Color logic
    let color = "text-green-500";
    let strokeColor = "#22c55e"; // green-500

    if (score < 50) {
        color = "text-red-500";
        strokeColor = "#ef4444"; // red-500
    } else if (score < 80) {
        color = "text-yellow-500";
        strokeColor = "#eab308"; // yellow-500
    }

    // SVG Gauge Calculations
    const size = compact ? 60 : 160;
    const radius = size / 2;
    const stroke = compact ? 4 : 10;
    const normalizedRadius = radius - stroke;
    const circumference = normalizedRadius * 2 * Math.PI;
    const strokeDashoffset = circumference - (score / 100) * circumference;

    return (
        <div className="flex flex-col items-center justify-center">
            <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
                {loading ? (
                    <div className="flex flex-col items-center gap-1">
                        <div className={`animate-spin rounded-full ${compact ? "h-6 w-6 border-b" : "h-12 w-12 border-b-2"} ${isDark ? "border-blue-500" : "border-blue-600"}`}></div>
                        {!compact && <span className="text-[10px] uppercase tracking-wider font-semibold opacity-50">Analyzing...</span>}
                    </div>
                ) : (
                    <>
                        {/* Background Circle */}
                        <svg
                            height={size}
                            width={size}
                            className="transform -rotate-90"
                        >
                            <circle
                                stroke={isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)"}
                                strokeWidth={stroke}
                                fill="transparent"
                                r={normalizedRadius}
                                cx={radius}
                                cy={radius}
                            />
                            <circle
                                stroke={strokeColor}
                                strokeDasharray={circumference + " " + circumference}
                                style={{ strokeDashoffset, transition: "stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1)" }}
                                strokeWidth={stroke}
                                strokeLinecap="round"
                                fill="transparent"
                                r={normalizedRadius}
                                cx={radius}
                                cy={radius}
                            />
                        </svg>
                        {/* Score Text */}
                        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                            <span className={`${compact ? "text-lg" : "text-4xl"} font-bold tracking-tight ${color} tabular-nums leading-none`}>
                                {score}
                            </span>
                            {!compact && (
                                <span className={`text-[10px] uppercase tracking-widest font-bold mt-1 ${isDark ? "text-slate-500" : "text-slate-400"}`}>
                                    SCORE
                                </span>
                            )}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
