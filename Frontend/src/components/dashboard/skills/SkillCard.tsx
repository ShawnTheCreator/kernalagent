'use client';

import { motion } from 'framer-motion';
import { Trash2, Edit2, Play } from 'lucide-react';
import { formatRelativeTime } from '@/lib/mockApi';
import type { Skill } from '@/stores/dashboardStore';

interface SkillCardProps {
    skill: Skill;
    onDelete?: () => void;
    onEdit?: () => void;
    onPlay?: () => void;
}

export function SkillCard({ skill, onDelete, onEdit, onPlay }: SkillCardProps) {
    const confidenceColors = {
        high: 'bg-emerald-400',
        medium: 'bg-amber-400',
        low: 'bg-red-400',
    };

    const confidenceLabels = {
        high: 'High',
        medium: 'Medium',
        low: 'Low',
    };

    const confidenceWidth = {
        high: 'w-full',
        medium: 'w-2/3',
        low: 'w-1/3',
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="bg-[#0a0a0a] border border-white/[0.05] rounded-xl p-4 hover:border-white/10 transition-colors group relative"
        >
            {/* Action buttons (visible on hover or always on mobile) */}
            {(onDelete || onEdit || onPlay) && (
                <div className="absolute top-2 right-2 flex gap-1 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity">
                    {onPlay && (
                        <button
                            onClick={(e) => { e.stopPropagation(); onPlay(); }}
                            className="p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
                            title="Run skill"
                        >
                            <Play size={12} />
                        </button>
                    )}
                    {onEdit && (
                        <button
                            onClick={(e) => { e.stopPropagation(); onEdit(); }}
                            className="p-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors"
                            title="Edit skill"
                        >
                            <Edit2 size={12} />
                        </button>
                    )}
                    {onDelete && (
                        <button
                            onClick={(e) => { e.stopPropagation(); onDelete(); }}
                            className="p-1.5 rounded-lg bg-zinc-800 hover:bg-red-600 text-zinc-400 hover:text-white transition-colors"
                            title="Delete skill"
                        >
                            <Trash2 size={12} />
                        </button>
                    )}
                </div>
            )}

            {/* Header */}
            <div className="flex items-start justify-between mb-2 pr-16">
                <h3 className="text-sm font-medium text-white group-hover:text-zinc-200 transition-colors">
                    {skill.name}
                </h3>
                <span className="text-[10px] font-mono text-zinc-600">
                    {skill.executionCount}x
                </span>
            </div>

            {/* Description */}
            <p className="text-xs text-zinc-500 mb-3 leading-relaxed">
                {skill.description}
            </p>

            {/* Confidence meter */}
            <div className="mb-3">
                <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] uppercase tracking-widest text-zinc-600">Confidence</span>
                    <span className="text-[10px] font-mono text-zinc-500">{confidenceLabels[skill.confidence]}</span>
                </div>
                <div className="h-1 bg-white/[0.05] rounded-full overflow-hidden">
                    <div className={`h-full ${confidenceWidth[skill.confidence]} ${confidenceColors[skill.confidence]} rounded-full`} />
                </div>
            </div>

            {/* Last executed */}
            {skill.lastExecuted && (
                <div className="text-[10px] text-zinc-600">
                    Last used: {formatRelativeTime(skill.lastExecuted)}
                </div>
            )}
        </motion.div>
    );
}

