'use client';

/**
 * Activity Page - Real-time Agent Execution Log
 * 
 * Full-page view of the agent's activity timeline with detailed event display.
 * Uses the production-grade useAgentSocket hook for connection management.
 */

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
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
            className="p-4 flex items-center gap-4 hover:bg-zinc-900/40 transition-all border-b border-zinc-900 last:border-b-0"
        >
            <div className={`p-2.5 rounded-lg ${style.bgColor} ${style.color}`}>
                {getActionIcon(event.actionType)}
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                    <span className={`text-[10px] font-mono font-bold uppercase ${style.color}`}>
                        {style.label}
                    </span>
                    <span className="text-[9px] text-zinc-600">{timeAgo}</span>
                </div>
                <p className="text-sm text-zinc-300">{event.label}</p>
                {event.description && (
                    <p className="text-xs text-zinc-500 mt-0.5">{event.description}</p>
                )}
            </div>
        </motion.div>
    );
}

function ConnectionIndicator({ state }: { state: ConnectionState }) {
    switch (state) {
        case 'LIVE':
            return (
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
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

function EmptyState() {
    return (
        <div className="p-16 text-center">
            <Brain size={40} className="text-zinc-700 mx-auto mb-4" />
            <p className="text-sm text-zinc-500">Waiting for agent activity…</p>
            <p className="text-[10px] text-zinc-700 mt-1">Actions will appear here in real-time</p>
        </div>
    );
}

function OfflineState({ onReconnect }: { onReconnect: () => void }) {
    return (
        <div className="p-16 text-center">
            <WifiOff size={40} className="text-zinc-600 mx-auto mb-4" />
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
// Main Activity Page Component
// ============================================================================

export default function ActivityPage() {
    const { events, connectionState, reconnect } = useAgentSocket();
    const latestEvent = events[0];
    const currentActionType = latestEvent?.actionType;

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="space-y-6"
        >
            {/* Header */}
            <div>
                <h1 className="text-xl font-semibold text-white">Activity</h1>
                <p className="text-sm text-zinc-600 mt-1">Real-time agent execution log</p>
            </div>

            {/* Activity Timeline */}
            <div className="bg-zinc-950 border border-zinc-900 rounded-2xl overflow-hidden">
                {/* Header */}
                <div className="p-5 border-b border-zinc-900 flex justify-between items-center bg-zinc-900/20">
                    <div className="flex items-center gap-3">
                        <Brain size={16} className="text-zinc-500" />
                        <h3 className="text-sm font-medium text-zinc-300">Activity Timeline</h3>
                    </div>
                    <div className="flex items-center gap-4">
                        <ConnectionIndicator state={connectionState} />
                        {currentActionType && (
                            <span className={`text-[10px] font-mono font-bold uppercase ${ACTION_STYLES[currentActionType]?.color || 'text-zinc-400'}`}>
                                {ACTION_STYLES[currentActionType]?.label || currentActionType}
                            </span>
                        )}
                    </div>
                </div>

                {/* Timeline */}
                <div className="max-h-[calc(100vh-280px)] overflow-y-auto">
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

                {/* Footer */}
                {events.length > 0 && (
                    <div className="p-4 border-t border-zinc-900 bg-zinc-900/10">
                        <span className="text-[10px] font-mono text-zinc-600">
                            {events.length} events • Last sync: now
                        </span>
                    </div>
                )}
            </div>
        </motion.div>
    );
}
