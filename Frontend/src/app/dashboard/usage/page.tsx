'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { BarChart3 } from 'lucide-react';

// Token usage data
const last7Days = [
    { day: 'Mon', tokens: 12400 },
    { day: 'Tue', tokens: 18200 },
    { day: 'Wed', tokens: 9800 },
    { day: 'Thu', tokens: 22100 },
    { day: 'Fri', tokens: 15600 },
    { day: 'Sat', tokens: 8900 },
    { day: 'Sun', tokens: 11300 },
];

const last30Days = [
    { day: '1', tokens: 12400 }, { day: '2', tokens: 18200 }, { day: '3', tokens: 9800 },
    { day: '4', tokens: 22100 }, { day: '5', tokens: 15600 }, { day: '6', tokens: 8900 },
    { day: '7', tokens: 11300 }, { day: '8', tokens: 14500 }, { day: '9', tokens: 19200 },
    { day: '10', tokens: 16800 }, { day: '11', tokens: 21000 }, { day: '12', tokens: 13400 },
    { day: '13', tokens: 17600 }, { day: '14', tokens: 10200 }, { day: '15', tokens: 24300 },
    { day: '16', tokens: 18900 }, { day: '17', tokens: 15100 }, { day: '18', tokens: 20400 },
    { day: '19', tokens: 12700 }, { day: '20', tokens: 16300 }, { day: '21', tokens: 19800 },
    { day: '22', tokens: 14200 }, { day: '23', tokens: 22600 }, { day: '24', tokens: 17100 },
    { day: '25', tokens: 11800 }, { day: '26', tokens: 25000 }, { day: '27', tokens: 18400 },
    { day: '28', tokens: 13900 }, { day: '29', tokens: 21500 }, { day: '30', tokens: 16700 },
];

type TimeRange = '7d' | '30d';

export default function UsagePage() {
    const [timeRange, setTimeRange] = useState<TimeRange>('7d');

    const data = timeRange === '7d' ? last7Days : last30Days;
    const maxTokens = Math.max(...data.map(d => d.tokens));
    const totalTokens = data.reduce((sum, d) => sum + d.tokens, 0);
    const avgTokens = Math.round(totalTokens / data.length);

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="space-y-8"
        >
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-black text-white tracking-tighter uppercase">Usage</h1>
                    <p className="text-zinc-500 text-sm mt-1">Token consumption over time</p>
                </div>

                {/* Time Range Toggle */}
                <div className="flex bg-zinc-900 rounded-lg p-1 border border-zinc-800">
                    <button
                        onClick={() => setTimeRange('7d')}
                        className={`px-4 py-2 rounded-md text-[10px] font-bold uppercase tracking-widest transition-all ${timeRange === '7d'
                                ? 'bg-white text-black'
                                : 'text-zinc-500 hover:text-white'
                            }`}
                    >
                        Last 7 Days
                    </button>
                    <button
                        onClick={() => setTimeRange('30d')}
                        className={`px-4 py-2 rounded-md text-[10px] font-bold uppercase tracking-widest transition-all ${timeRange === '30d'
                                ? 'bg-white text-black'
                                : 'text-zinc-500 hover:text-white'
                            }`}
                    >
                        Last 30 Days
                    </button>
                </div>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="bg-zinc-900/40 border border-zinc-800 rounded-xl p-5">
                    <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">Total Tokens</div>
                    <div className="text-2xl font-black text-white font-mono">{totalTokens.toLocaleString()}</div>
                </div>
                <div className="bg-zinc-900/40 border border-zinc-800 rounded-xl p-5">
                    <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">Daily Average</div>
                    <div className="text-2xl font-black text-white font-mono">{avgTokens.toLocaleString()}</div>
                </div>
                <div className="bg-zinc-900/40 border border-zinc-800 rounded-xl p-5 hidden md:block">
                    <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">Peak Day</div>
                    <div className="text-2xl font-black text-white font-mono">{maxTokens.toLocaleString()}</div>
                </div>
            </div>

            {/* Bar Chart */}
            <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6">
                <div className="flex items-center gap-2 mb-6">
                    <BarChart3 size={16} className="text-zinc-500" />
                    <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-zinc-500">
                        Tokens Used ({timeRange === '7d' ? 'Last 7 Days' : 'Last 30 Days'})
                    </h3>
                </div>

                {/* Chart */}
                <div className="h-64 flex items-end gap-1 md:gap-2">
                    {data.map((item, index) => {
                        const height = (item.tokens / maxTokens) * 100;
                        return (
                            <motion.div
                                key={index}
                                initial={{ height: 0 }}
                                animate={{ height: `${height}%` }}
                                transition={{ duration: 0.5, delay: index * 0.02 }}
                                className="flex-1 group relative"
                            >
                                <div
                                    className="w-full h-full bg-blue-500/20 hover:bg-blue-500/40 rounded-t transition-colors cursor-pointer border-t-2 border-blue-500"
                                />

                                {/* Tooltip */}
                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-zinc-800 rounded text-[10px] font-mono text-white whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                                    {item.tokens.toLocaleString()} tokens
                                </div>
                            </motion.div>
                        );
                    })}
                </div>

                {/* X-axis labels */}
                <div className="flex gap-1 md:gap-2 mt-2">
                    {data.map((item, index) => (
                        <div key={index} className="flex-1 text-center">
                            <span className={`text-[8px] md:text-[9px] font-mono text-zinc-600 ${timeRange === '30d' && index % 5 !== 0 ? 'hidden md:inline' : ''}`}>
                                {timeRange === '7d' ? item.day : item.day}
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Info */}
            <div className="text-[10px] text-zinc-600 text-center">
                Tokens are counted for all LLM API calls including vision, reasoning, and execution.
            </div>
        </motion.div>
    );
}
