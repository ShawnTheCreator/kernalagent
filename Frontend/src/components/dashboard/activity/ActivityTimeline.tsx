'use client';

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, RefreshCw } from 'lucide-react';
import { useDashboardStore } from '@/stores/dashboardStore';
import { startActivitySimulation, mockActivities } from '@/lib/mockApi';
import { ActivityEvent } from './ActivityEvent';

interface ActivityTimelineProps {
    limit?: number;
    showHeader?: boolean;
}

export function ActivityTimeline({ limit, showHeader = true }: ActivityTimelineProps) {
    const { activities, addActivity, currentState } = useDashboardStore();

    // Start activity simulation on mount
    useEffect(() => {
        // Add initial mock activities
        mockActivities.forEach((event, index) => {
            setTimeout(() => addActivity(event), index * 100);
        });

        // Start real-time simulation
        const cleanup = startActivitySimulation(addActivity);
        return cleanup;
    }, [addActivity]);

    const displayActivities = limit ? activities.slice(0, limit) : activities;

    return (
        <div className="flex flex-col h-full bg-[#0a0a0a] border border-white/[0.05] rounded-xl overflow-hidden">
            {/* Header */}
            {showHeader && (
                <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.05]">
                    <div className="flex items-center gap-2">
                        <Brain size={16} className="text-zinc-500" />
                        <h2 className="text-sm font-medium text-zinc-300">Activity Timeline</h2>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-zinc-600 uppercase">
                            {currentState}
                        </span>
                        <motion.div
                            animate={currentState !== 'IDLE' ? { rotate: 360 } : {}}
                            transition={{ duration: 2, repeat: currentState !== 'IDLE' ? Infinity : 0, ease: 'linear' }}
                        >
                            <RefreshCw size={12} className="text-zinc-600" />
                        </motion.div>
                    </div>
                </div>
            )}

            {/* Timeline */}
            <div className="flex-1 overflow-y-auto scrollbar-thin">
                {displayActivities.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full py-12 text-center px-4">
                        <div className="w-12 h-12 rounded-full bg-white/[0.02] flex items-center justify-center mb-4">
                            <Brain size={20} className="text-zinc-600" />
                        </div>
                        <p className="text-sm text-zinc-500">Awaiting activity</p>
                        <p className="text-[10px] text-zinc-700 mt-1">Events will appear here</p>
                    </div>
                ) : (
                    <AnimatePresence mode="popLayout">
                        {displayActivities.map((event, index) => (
                            <ActivityEvent
                                key={event.id}
                                event={event}
                                isLatest={index === 0}
                            />
                        ))}
                    </AnimatePresence>
                )}
            </div>

            {/* Footer */}
            {activities.length > 0 && (
                <div className="px-4 py-2 border-t border-white/[0.03] bg-white/[0.01]">
                    <span className="text-[10px] font-mono text-zinc-600">
                        {activities.length} events • Last sync: now
                    </span>
                </div>
            )}
        </div>
    );
}
