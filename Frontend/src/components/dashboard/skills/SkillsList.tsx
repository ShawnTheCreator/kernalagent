'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Sparkles } from 'lucide-react';
import { SkillCard } from './SkillCard';
import { mockSkills } from '@/lib/mockApi';

export function SkillsList() {
    const [searchQuery, setSearchQuery] = useState('');

    const filteredSkills = mockSkills.filter(skill =>
        skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        skill.description.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Sparkles size={16} className="text-zinc-500" />
                    <h2 className="text-sm font-medium text-zinc-300">Learned Skills</h2>
                    <span className="text-[10px] font-mono text-zinc-600">{mockSkills.length} total</span>
                </div>
            </div>

            {/* Search */}
            <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" />
                <input
                    type="text"
                    placeholder="Search skills..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-white/[0.03] border border-white/[0.05] rounded-lg pl-9 pr-4 py-2.5 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-white/20 transition-colors"
                />
            </div>

            {/* Skills Grid */}
            <motion.div
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
                initial="hidden"
                animate="visible"
                variants={{
                    hidden: {},
                    visible: {
                        transition: { staggerChildren: 0.05 }
                    }
                }}
            >
                {filteredSkills.map((skill) => (
                    <SkillCard key={skill.id} skill={skill} />
                ))}
            </motion.div>

            {filteredSkills.length === 0 && (
                <div className="text-center py-12">
                    <p className="text-sm text-zinc-500">No skills found matching "{searchQuery}"</p>
                </div>
            )}
        </div>
    );
}
