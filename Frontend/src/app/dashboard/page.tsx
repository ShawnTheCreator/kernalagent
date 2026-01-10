'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Activity,
    Database,
    Cpu,
    Globe,
    Brain,
    Eye,
    Map,
    Play,
    AlertTriangle,
    Loader2
} from 'lucide-react';
import { useSocket, type ActionMessage } from '@/hooks/useSocket';
import { getActionStyle, formatRelativeTime } from '@/lib/actionUtils';

// Metric Card Component
function MetricCard({ label, value, trend, icon: Icon }: {
    label: string;
    value: string;
    trend?: string;
    icon: React.ComponentType<{ size?: number; className?: string }>
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="bg-zinc-900/40 border border-zinc-800 p-5 rounded-xl space-y-4"
        >
            <div className="flex justify-between items-start">
                <div className="p-2 bg-zinc-800/50 rounded-lg">
                    <Icon size={14} className="text-zinc-400" />
                </div>
                {trend && (
                    <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                        {trend}
                    </span>
                )}
            </div>
            <div>
                <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">{label}</div>
                <div className="text-2xl font-black tracking-tight text-white font-mono">{value}</div>
            </div>
        </motion.div>
    );
}

// Action icon mapping
function getActionIcon(actionType: string) {
    const type = actionType.toUpperCase();
    switch (type) {
        case 'THINKING': return <Brain size={16} />;
        case 'OBSERVING': return <Eye size={16} />;
        case 'PLANNING': return <Map size={16} />;
        case 'FAILED':
        case 'ERROR': return <AlertTriangle size={16} />;
        default: return <Play size={16} />;
    }
}

// Live Action Item Component
function ActionItem({ action }: { action: ActionMessage }) {
    const style = getActionStyle(action.action_type);
    const [timeAgo, setTimeAgo] = useState(formatRelativeTime(action.timestamp));

    // Update relative time every 10 seconds
    useEffect(() => {
        const interval = setInterval(() => {
            setTimeAgo(formatRelativeTime(action.timestamp));
        }, 10000);
        return () => clearInterval(interval);
    }, [action.timestamp]);

    return (
        <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="p-4 flex items-center gap-4 hover:bg-zinc-900/40 transition-all"
        >
            <div className={`p-2 rounded-lg bg-zinc-900 ${style.color}`}>
                {getActionIcon(action.action_type)}
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-mono font-bold uppercase ${style.color}`}>
                        {style.label}
                    </span>
                    <span className="text-[9px] text-zinc-600">{timeAgo}</span>
                </div>
                <p className="text-sm text-zinc-300 mt-0.5 truncate">{action.explanation}</p>
            </div>
        </motion.div>
    );
}

// Connection Status Indicator
function ConnectionStatus({ status, isConnected }: { status: string; isConnected: boolean }) {
    if (isConnected) {
        return (
            <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                <span className="text-[10px] font-mono text-emerald-400 uppercase">Live</span>
            </div>
        );
    }

    if (status === 'connecting' || status === 'disconnected') {
        return (
            <div className="flex items-center gap-2">
                <Loader2 size={12} className="text-amber-400 animate-spin" />
                <span className="text-[10px] font-mono text-amber-400 uppercase">Reconnecting…</span>
            </div>
        );
    }

    return (
        <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-zinc-600" />
            <span className="text-[10px] font-mono text-zinc-500 uppercase">Offline</span>
        </div>
    );
}

export default function DashboardPage() {
    const { actions, status, isConnected } = useSocket();

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="space-y-10"
        >
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-black text-white tracking-tighter uppercase italic">Control Room</h1>
                    <p className="text-zinc-500 text-sm mt-1">Real-time telemetry and autonomous process management.</p>
                </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                <MetricCard label="CPU Latency" value="14.2ms" trend="-2%" icon={Activity} />
                <MetricCard label="Mem Efficiency" value="94.1%" icon={Database} />
                <MetricCard label="Logic Cycles" value="1.2M" trend="+12%" icon={Cpu} />
                <MetricCard label="Global Sync" value="Live" icon={Globe} />
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Real-time Action Panel */}
                <div className="lg:col-span-2 bg-zinc-950 border border-zinc-900 rounded-2xl overflow-hidden shadow-2xl">
                    <div className="p-6 border-b border-zinc-900 flex justify-between items-center bg-zinc-900/20">
                        <div className="flex items-center gap-3">
                            <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
                            <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-white">Real-time Actions</h3>
                        </div>
                        <ConnectionStatus status={status} isConnected={isConnected} />
                    </div>

                    <div className="divide-y divide-zinc-900 max-h-[400px] overflow-y-auto">
                        {actions.length === 0 ? (
                            <div className="p-12 text-center">
                                <Brain size={32} className="text-zinc-700 mx-auto mb-4" />
                                <p className="text-sm text-zinc-500">Waiting for agent activity...</p>
                                <p className="text-[10px] text-zinc-700 mt-1">Actions will appear here in real-time</p>
                            </div>
                        ) : (
                            <AnimatePresence mode="popLayout">
                                {actions.map((action) => (
                                    <ActionItem key={action.id} action={action} />
                                ))}
                            </AnimatePresence>
                        )}
                    </div>

                    {actions.length > 0 && (
                        <div className="p-4 border-t border-zinc-900 bg-zinc-900/10">
                            <span className="text-[10px] font-mono text-zinc-600">
                                {actions.length} events • Last sync: now
                            </span>
                        </div>
                    )}
                </div>

                {/* Agent Status Panel */}
                <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6 space-y-6">
                    <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-zinc-500">Agent Status</h3>

                    {/* Agent Identity */}
                    <div className="flex items-center gap-4 p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
                        <div className="w-12 h-12 rounded-xl bg-zinc-800 border border-zinc-700 flex items-center justify-center">
                            <Brain size={24} className="text-blue-400" />
                        </div>
                        <div>
                            <div className="text-sm font-black text-white">Kernel Agent</div>
                            <div className="flex items-center gap-2 mt-1">
                                {isConnected ? (
                                    <>
                                        <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                                        <span className="text-[10px] font-mono text-emerald-400 uppercase">Active</span>
                                    </>
                                ) : (
                                    <>
                                        <div className="w-2 h-2 rounded-full bg-amber-400" />
                                        <span className="text-[10px] font-mono text-amber-400 uppercase">Reconnecting</span>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Stats */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="p-3 bg-zinc-900/30 rounded-lg">
                            <div className="text-[9px] font-black text-zinc-600 uppercase">Actions Today</div>
                            <div className="text-lg font-mono font-bold text-white mt-1">{actions.length || 0}</div>
                        </div>
                        <div className="p-3 bg-zinc-900/30 rounded-lg">
                            <div className="text-[9px] font-black text-zinc-600 uppercase">Success Rate</div>
                            <div className="text-lg font-mono font-bold text-emerald-400 mt-1">98.7%</div>
                        </div>
                    </div>

                    {/* System Info */}
                    <div className="space-y-3 pt-4 border-t border-zinc-800">
                        <div className="flex justify-between text-xs">
                            <span className="text-zinc-500">Environment</span>
                            <span className="font-mono text-white">Windows 11</span>
                        </div>
                        <div className="flex justify-between text-xs">
                            <span className="text-zinc-500">Version</span>
                            <span className="font-mono text-white">v0.1.2-alpha</span>
                        </div>
                        <div className="flex justify-between text-xs">
                            <span className="text-zinc-500">WebSocket</span>
                            <span className={`font-mono ${isConnected ? 'text-emerald-400' : 'text-amber-400'}`}>
                                {isConnected ? 'Connected' : 'Reconnecting'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </motion.div>
    );
}
