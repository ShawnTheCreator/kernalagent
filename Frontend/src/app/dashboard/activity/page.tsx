'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Eye, Map, Play, AlertTriangle, Loader2 } from 'lucide-react';
import { useSocket, type ActionMessage } from '@/hooks/useSocket';
import { getActionStyle, formatRelativeTime } from '@/lib/actionUtils';

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
            className="p-4 flex items-center gap-4 hover:bg-zinc-900/40 transition-all border-b border-zinc-900 last:border-b-0"
        >
            <div className={`p-2.5 rounded-lg ${style.bgColor} ${style.color}`}>
                {getActionIcon(action.action_type)}
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                    <span className={`text-[10px] font-mono font-bold uppercase ${style.color}`}>
                        {style.label}
                    </span>
                    <span className="text-[9px] text-zinc-600">{timeAgo}</span>
                </div>
                <p className="text-sm text-zinc-300">{action.explanation}</p>
            </div>
        </motion.div>
    );
}

// Connection Status Indicator
function ConnectionStatus({ status, isConnected }: { status: string; isConnected: boolean }) {
    if (isConnected) {
        return (
            <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
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

export default function ActivityPage() {
    const { actions, status, isConnected } = useSocket();
    const latestAction = actions[0];
    const currentState = latestAction?.action_type || 'IDLE';

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
                        <ConnectionStatus status={status} isConnected={isConnected} />
                        {latestAction && (
                            <span className={`text-[10px] font-mono font-bold uppercase ${getActionStyle(currentState).color}`}>
                                {currentState}
                            </span>
                        )}
                    </div>
                </div>

                {/* Timeline */}
                <div className="max-h-[calc(100vh-280px)] overflow-y-auto">
                    {actions.length === 0 ? (
                        <div className="p-16 text-center">
                            <Brain size={40} className="text-zinc-700 mx-auto mb-4" />
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

                {/* Footer */}
                {actions.length > 0 && (
                    <div className="p-4 border-t border-zinc-900 bg-zinc-900/10">
                        <span className="text-[10px] font-mono text-zinc-600">
                            {actions.length} events • Last sync: now
                        </span>
                    </div>
                )}
            </div>
        </motion.div>
    );
}
