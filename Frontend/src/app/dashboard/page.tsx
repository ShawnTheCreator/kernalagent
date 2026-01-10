'use client';

/**
 * Dashboard Page - Control Room
 * 
 * Real-time AI agent monitoring dashboard with live WebSocket streaming.
 * Uses the production-grade useAgentSocket hook for connection management.
 */

import { useState, useEffect, useMemo } from 'react';
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
    Loader2,
    WifiOff,
    MousePointer,
    Type,
    ArrowDownUp,
    Clock,
    AlertTriangle
} from 'lucide-react';
import { useAgentSocket } from '@/hooks/useAgentSocket';
import type { AgentEvent, ActionType, ConnectionState } from '@/types/agentEvents';
import { ACTION_STYLES } from '@/types/agentEvents';

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format timestamp to relative time string
 */
function formatRelativeTime(timestamp: number): string {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 5) return 'now';
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
}

/**
 * Get icon component for a given action type
 */
function getActionIcon(actionType: ActionType) {
    switch (actionType) {
        case 'CLICK': return <MousePointer size={16} />;
        case 'TYPE': return <Type size={16} />;
        case 'SCROLL': return <ArrowDownUp size={16} />;
        case 'WAIT': return <Clock size={16} />;
        case 'ERROR': return <AlertTriangle size={16} />;
        case 'THINKING': return <Brain size={16} />;
        case 'OBSERVING': return <Eye size={16} />;
        case 'PLANNING': return <Map size={16} />;
        case 'EXECUTING': return <Play size={16} />;
        default: return <Brain size={16} />;
    }
}

// ============================================================================
// Sub-Components
// ============================================================================

/**
 * Metric Card - Displays a single metric with optional trend
 */
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

/**
 * Event Item - Displays a single event in the timeline with action-specific badge colors
 */
function EventItem({ event }: { event: AgentEvent }) {
    const style = ACTION_STYLES[event.actionType] || ACTION_STYLES.UNKNOWN;
    const [timeAgo, setTimeAgo] = useState(formatRelativeTime(event.timestamp));

    useEffect(() => {
        const interval = setInterval(() => {
            setTimeAgo(formatRelativeTime(event.timestamp));
        }, 10000);
        return () => clearInterval(interval);
    }, [event.timestamp]);

    return (
        <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="p-4 flex items-center gap-4 hover:bg-zinc-900/40 transition-all"
        >
            <div className={`p-2 rounded-lg ${style.bgColor} ${style.color}`}>
                {getActionIcon(event.actionType)}
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-mono font-bold uppercase ${style.color}`}>
                        {style.label}
                    </span>
                    <span className="text-[9px] text-zinc-600">{timeAgo}</span>
                </div>
                <p className="text-sm text-zinc-300 mt-0.5 truncate">{event.label}</p>
            </div>
        </motion.div>
    );
}

/**
 * Connection Status Indicator - Shows current WebSocket connection state
 */
function ConnectionIndicator({ state }: { state: ConnectionState }) {
    switch (state) {
        case 'LIVE':
            return (
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                    <span className="text-[10px] font-mono text-emerald-400 uppercase">Live</span>
                </div>
            );

        case 'CONNECTING':
        case 'RECONNECTING':
            return (
                <div className="flex items-center gap-2">
                    <Loader2 size={12} className="text-amber-400 animate-spin" />
                    <span className="text-[10px] font-mono text-amber-400 uppercase">
                        {state === 'CONNECTING' ? 'Connecting…' : 'Reconnecting…'}
                    </span>
                </div>
            );

        case 'DISCONNECTED':
            return (
                <div className="flex items-center gap-2">
                    <WifiOff size={12} className="text-zinc-500" />
                    <span className="text-[10px] font-mono text-zinc-500 uppercase">Offline</span>
                </div>
            );
    }
}

/**
 * Empty State - Shown when connected but no events
 */
function EmptyState() {
    return (
        <div className="p-12 text-center">
            <Brain size={32} className="text-zinc-700 mx-auto mb-4" />
            <p className="text-sm text-zinc-500">Waiting for agent activity…</p>
            <p className="text-[10px] text-zinc-700 mt-1">Actions will appear here in real-time</p>
        </div>
    );
}

/**
 * Offline State - Shown when disconnected
 */
function OfflineState({ onReconnect }: { onReconnect: () => void }) {
    return (
        <div className="p-12 text-center">
            <WifiOff size={32} className="text-zinc-600 mx-auto mb-4" />
            <p className="text-sm text-zinc-400">Agent offline</p>
            <p className="text-[10px] text-zinc-600 mt-1">Connection lost to agent server</p>
            <button
                onClick={onReconnect}
                className="mt-4 px-4 py-2 text-xs font-mono bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg transition-colors"
            >
                Retry Connection
            </button>
        </div>
    );
}

// ============================================================================
// Main Dashboard Component
// ============================================================================

export default function DashboardPage() {
    const { events, connectionState, isLive, reconnect } = useAgentSocket();

    const connectionStatusText = useMemo(() => {
        switch (connectionState) {
            case 'LIVE': return 'Connected';
            case 'CONNECTING': return 'Connecting';
            case 'RECONNECTING': return 'Reconnecting';
            case 'DISCONNECTED': return 'Disconnected';
        }
    }, [connectionState]);

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
                <MetricCard label="Global Sync" value={isLive ? "Live" : "Offline"} icon={Globe} />
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Real-time Action Panel */}
                <div className="lg:col-span-2 bg-zinc-950 border border-zinc-900 rounded-2xl overflow-hidden shadow-2xl">
                    <div className="p-6 border-b border-zinc-900 flex justify-between items-center bg-zinc-900/20">
                        <div className="flex items-center gap-3">
                            <div className={`w-2 h-2 rounded-full ${isLive ? 'bg-blue-500 animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.5)]' : 'bg-zinc-600'}`} />
                            <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-white">Real-time Actions</h3>
                        </div>
                        <ConnectionIndicator state={connectionState} />
                    </div>

                    <div className="divide-y divide-zinc-900 max-h-[400px] overflow-y-auto">
                        {connectionState === 'DISCONNECTED' && events.length === 0 ? (
                            <OfflineState onReconnect={reconnect} />
                        ) : events.length === 0 ? (
                            <EmptyState />
                        ) : (
                            <AnimatePresence mode="popLayout">
                                {events.map((event) => (
                                    <EventItem key={event.id} event={event} />
                                ))}
                            </AnimatePresence>
                        )}
                    </div>

                    {events.length > 0 && (
                        <div className="p-4 border-t border-zinc-900 bg-zinc-900/10">
                            <span className="text-[10px] font-mono text-zinc-600">
                                {events.length} events • Last sync: now
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
                                {isLive ? (
                                    <>
                                        <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                                        <span className="text-[10px] font-mono text-emerald-400 uppercase">Active</span>
                                    </>
                                ) : connectionState === 'DISCONNECTED' ? (
                                    <>
                                        <div className="w-2 h-2 rounded-full bg-zinc-500" />
                                        <span className="text-[10px] font-mono text-zinc-500 uppercase">Offline</span>
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
                            <div className="text-lg font-mono font-bold text-white mt-1">{events.length || 0}</div>
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
                            <span className={`font-mono ${isLive ? 'text-emerald-400' : connectionState === 'DISCONNECTED' ? 'text-zinc-500' : 'text-amber-400'}`}>
                                {connectionStatusText}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </motion.div>
    );
}
