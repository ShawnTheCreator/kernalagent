'use client';

import { motion } from 'framer-motion';
import { Brain, Eye, Map, Play, AlertTriangle, Clock } from 'lucide-react';
import { formatRelativeTime } from '@/lib/mockApi';
import type { ActivityEvent as ActivityEventType, ActivityState } from '@/stores/dashboardStore';

// State configuration
const stateConfig: Record<ActivityState, { color: string; bgColor: string; icon: React.ReactNode; label: string }> = {
    THINKING: { color: 'text-violet-400', bgColor: 'bg-violet-500/10', icon: <Brain size={14} />, label: 'Thinking' },
    OBSERVING: { color: 'text-blue-400', bgColor: 'bg-blue-500/10', icon: <Eye size={14} />, label: 'Observing' },
    PLANNING: { color: 'text-amber-400', bgColor: 'bg-amber-500/10', icon: <Map size={14} />, label: 'Planning' },
    EXECUTING: { color: 'text-emerald-400', bgColor: 'bg-emerald-500/10', icon: <Play size={14} />, label: 'Executing' },
    ERROR: { color: 'text-red-400', bgColor: 'bg-red-500/10', icon: <AlertTriangle size={14} />, label: 'Error' },
    IDLE: { color: 'text-zinc-400', bgColor: 'bg-zinc-500/10', icon: <Clock size={14} />, label: 'Idle' },
};

interface ActivityEventProps {
    event: ActivityEventType;
    isLatest?: boolean;
}

export function ActivityEvent({ event, isLatest = false }: ActivityEventProps) {
    const config = stateConfig[event.state];

    return (
        <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className={`
        relative flex gap-4 py-3 px-4 group cursor-pointer
        hover:bg-white/[0.02] transition-colors
        ${isLatest ? 'bg-white/[0.01]' : ''}
      `}
        >
            {/* Timeline line */}
            <div className="absolute left-[27px] top-0 bottom-0 w-px bg-white/[0.05]" />

            {/* Status dot */}
            <div className="relative z-10 shrink-0">
                <motion.div
                    animate={event.isNew ? { scale: [1, 1.2, 1] } : {}}
                    transition={{ duration: 0.3 }}
                    className={`w-6 h-6 rounded-full ${config.bgColor} flex items-center justify-center ${config.color}`}
                >
                    {config.icon}
                </motion.div>
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                    <span className={`text-[10px] font-mono uppercase tracking-wider ${config.color}`}>
                        {config.label}
                    </span>
                    <span className="text-[10px] font-mono text-zinc-600">
                        {formatRelativeTime(event.timestamp)}
                    </span>
                </div>
                <p className="text-sm text-zinc-300 leading-relaxed">
                    {event.title}
                </p>
                {event.description && (
                    <p className="text-xs text-zinc-600 mt-1 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity">
                        {event.description}
                    </p>
                )}
            </div>

            {/* Duration (if available) */}
            {event.duration && (
                <div className="shrink-0 text-[10px] font-mono text-zinc-600">
                    {event.duration}ms
                </div>
            )}
        </motion.div>
    );
}
