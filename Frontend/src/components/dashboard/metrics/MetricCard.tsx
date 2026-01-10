'use client';

import { motion, useSpring, useTransform } from 'framer-motion';
import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface MetricCardProps {
    label: string;
    value: number;
    suffix?: string;
    trend?: 'up' | 'down' | 'flat';
    trendValue?: string;
    icon?: React.ReactNode;
    sparklineData?: number[];
}

function MiniSparkline({ data }: { data: number[] }) {
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;

    const points = data.map((value, index) => {
        const x = (index / (data.length - 1)) * 100;
        const y = 100 - ((value - min) / range) * 100;
        return `${x},${y}`;
    }).join(' ');

    return (
        <svg viewBox="0 0 100 100" className="w-full h-8" preserveAspectRatio="none">
            <polyline
                points={points}
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                vectorEffect="non-scaling-stroke"
                className="text-zinc-700"
            />
        </svg>
    );
}

export function MetricCard({ label, value, suffix = '', trend, trendValue, icon, sparklineData }: MetricCardProps) {
    const spring = useSpring(0, { damping: 30, stiffness: 100 });
    const display = useTransform(spring, (v) => Math.floor(v));
    const [displayValue, setDisplayValue] = useState(0);

    useEffect(() => {
        spring.set(value);
    }, [spring, value]);

    useEffect(() => {
        const unsubscribe = display.on('change', (v) => setDisplayValue(v));
        return unsubscribe;
    }, [display]);

    const trendColors = {
        up: 'text-emerald-400',
        down: 'text-red-400',
        flat: 'text-zinc-500',
    };

    const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="bg-[#0a0a0a] border border-white/[0.05] rounded-xl p-4 flex flex-col"
        >
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] uppercase tracking-widest text-zinc-600">{label}</span>
                {icon && <div className="text-zinc-600">{icon}</div>}
            </div>

            {/* Value */}
            <div className="flex items-end gap-2 mb-2">
                <span className="text-3xl font-bold text-white tabular-nums">
                    {displayValue.toLocaleString()}{suffix}
                </span>
                {trend && trendValue && (
                    <div className={`flex items-center gap-0.5 mb-1 ${trendColors[trend]}`}>
                        <TrendIcon size={12} />
                        <span className="text-xs font-mono">{trendValue}</span>
                    </div>
                )}
            </div>

            {/* Sparkline */}
            {sparklineData && sparklineData.length > 0 && (
                <div className="mt-auto pt-2">
                    <MiniSparkline data={sparklineData} />
                </div>
            )}
        </motion.div>
    );
}
