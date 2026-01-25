'use client';

import { motion } from 'framer-motion';
import { Monitor, Eye, Mouse, Keyboard, Hash, Cpu } from 'lucide-react';
import { useDashboardStore } from '@/stores/dashboardStore';

interface StatusIndicatorProps {
    label: string;
    value: string | boolean;
    icon: React.ReactNode;
}

function StatusIndicator({ label, value, icon }: StatusIndicatorProps) {
    const isBoolean = typeof value === 'boolean';

    return (
        <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-2 text-zinc-500">
                {icon}
                <span className="text-xs">{label}</span>
            </div>
            {isBoolean ? (
                <div className={`w-2 h-2 rounded-full ${value ? 'bg-emerald-400' : 'bg-zinc-600'}`} />
            ) : (
                <span className="text-xs font-mono text-zinc-300">{value}</span>
            )}
        </div>
    );
}

export function AgentStatePanel() {
    const {
        agentStatus,
        os,
        version,
        visionEnabled,
        mouseEnabled,
        keyboardEnabled
    } = useDashboardStore();

    const statusColors = {
        live: 'bg-emerald-400',
        idle: 'bg-amber-400',
        offline: 'bg-zinc-500',
    };

    const statusLabels = {
        live: 'Active',
        idle: 'Idle',
        offline: 'Offline',
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="bg-[#0a0a0a] border border-white/[0.05] rounded-xl p-4"
        >
            {/* Header */}
            <div className="flex items-center gap-3 mb-4 pb-4 border-b border-white/[0.05]">
                <div className="w-10 h-10 bg-white/[0.03] border border-white/10 rounded-lg flex items-center justify-center">
                    <div className="w-5 h-5 border border-white flex items-center justify-center rotate-45">
                        <div className="w-2 h-2 bg-white" />
                    </div>
                </div>
                <div className="flex-1">
                    <h3 className="text-sm font-semibold text-white">Kernel</h3>
                    <div className="flex items-center gap-1.5 mt-0.5">
                        <motion.div
                            animate={agentStatus === 'live' ? {
                                opacity: [0.6, 1, 0.6],
                                scale: [0.95, 1, 0.95]
                            } : undefined}
                            transition={{ duration: 2, repeat: agentStatus === 'live' ? Infinity : 0, ease: 'easeInOut' }}
                            className={`w-1.5 h-1.5 rounded-full ${statusColors[agentStatus]}`}
                        />
                        <span className="text-[10px] font-mono text-zinc-500 uppercase">
                            {statusLabels[agentStatus]}
                        </span>
                    </div>
                </div>
            </div>

            {/* System Info */}
            <div className="space-y-1">
                <div className="text-[10px] uppercase tracking-widest text-zinc-600 mb-2">System</div>
                <StatusIndicator label="Environment" value={os} icon={<Monitor size={14} />} />
                <StatusIndicator label="Version" value={version} icon={<Hash size={14} />} />
            </div>

            {/* Capabilities */}
            <div className="space-y-1 mt-4 pt-4 border-t border-white/[0.05]">
                <div className="text-[10px] uppercase tracking-widest text-zinc-600 mb-2">Capabilities</div>
                <StatusIndicator label="Vision" value={visionEnabled} icon={<Eye size={14} />} />
                <StatusIndicator label="Mouse Control" value={mouseEnabled} icon={<Mouse size={14} />} />
                <StatusIndicator label="Keyboard" value={keyboardEnabled} icon={<Keyboard size={14} />} />
            </div>
        </motion.div>
    );
}
