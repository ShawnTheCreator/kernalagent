'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { List, PlusCircle } from 'lucide-react';
import { SkillsList, SkillEditor } from '@/components/dashboard/skills';
import { ActivityTimeline } from '@/components/dashboard/activity/ActivityTimeline';

export default function SkillsPage() {
    const [mode, setMode] = useState<'list' | 'create'>('list');

    return (
        <div className="h-[calc(100vh-140px)] flex gap-6">
            {/* Main Content */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex-1 flex flex-col space-y-6 overflow-hidden"
            >
                {/* Header */}
                <div className="flex items-center justify-between shrink-0">
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

                {/* Content Area */}
                <div className="flex-1 overflow-y-auto pr-2">
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
                </div>
            </motion.div>

            {/* Sidebar: Real-Time Actions */}
            <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
                className="w-80 hidden xl:flex flex-col border-l border-white/[0.05] pl-6"
            >
                <div className="h-full">
                    <ActivityTimeline />
                </div>
            </motion.div>
        </div>
    );
}
