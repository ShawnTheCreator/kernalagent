'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { List, PlusCircle } from 'lucide-react';
import { SkillsList, SkillEditor } from '@/components/dashboard/skills';

export default function SkillsPage() {
    const [mode, setMode] = useState<'list' | 'create'>('list');

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="space-y-6 h-[calc(100vh-180px)]"
        >
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-xl font-semibold text-white">Skills</h1>
                    <p className="text-sm text-zinc-600 mt-1">Learned capabilities and automation workflows</p>
                </div>

                {/* Mode Toggle */}
                <div className="flex items-center gap-2 bg-white/[0.03] rounded-lg p-1 border border-white/[0.05]">
                    <button
                        onClick={() => setMode('list')}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors ${mode === 'list'
                                ? 'bg-white/[0.08] text-white'
                                : 'text-zinc-500 hover:text-white'
                            }`}
                    >
                        <List size={14} />
                        View Skills
                    </button>
                    <button
                        onClick={() => setMode('create')}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors ${mode === 'create'
                                ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                                : 'text-zinc-500 hover:text-white'
                            }`}
                    >
                        <PlusCircle size={14} />
                        Create Skill
                    </button>
                </div>
            </div>

            {/* Content */}
            {mode === 'list' ? (
                <SkillsList />
            ) : (
                <div className="h-full">
                    <SkillEditor
                        onSave={() => setMode('list')}
                        onCancel={() => setMode('list')}
                    />
                </div>
            )}
        </motion.div>
    );
}
