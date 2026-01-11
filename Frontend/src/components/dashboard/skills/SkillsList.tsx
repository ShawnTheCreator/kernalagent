'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Search, Sparkles, RefreshCw, Loader2 } from 'lucide-react';
import { SkillCard } from './SkillCard';
import { fetchSkills } from '@/lib/skillsApi';
import { mockSkills } from '@/lib/mockApi';
import type { Skill } from '@/stores/dashboardStore';

export function SkillsList() {
    const [skills, setSkills] = useState<Skill[]>([]);
    const [loading, setLoading] = useState(true);
    const [useMock, setUseMock] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

    // Fetch skills on mount
    useEffect(() => {
        loadSkills();
    }, []);

    async function loadSkills() {
        setLoading(true);
        try {
            const data = await fetchSkills();
            if (data.length > 0) {
                setSkills(data);
                setUseMock(false);
            } else {
                // Fallback to mock data if backend empty or unavailable
                setSkills(mockSkills);
                setUseMock(true);
            }
        } catch {
            setSkills(mockSkills);
            setUseMock(true);
        }
        setLoading(false);
    }

    const filteredSkills = skills.filter(skill =>
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
                    <span className="text-[10px] font-mono text-zinc-600">{skills.length} total</span>
                    {useMock && (
                        <span className="text-[10px] px-1.5 py-0.5 bg-amber-500/20 text-amber-400 rounded">mock</span>
                    )}
                </div>
                <button
                    onClick={loadSkills}
                    disabled={loading}
                    className="p-1.5 rounded-lg hover:bg-white/5 transition-colors disabled:opacity-50"
                    title="Refresh skills"
                >
                    {loading ? (
                        <Loader2 size={14} className="text-zinc-500 animate-spin" />
                    ) : (
                        <RefreshCw size={14} className="text-zinc-500" />
                    )}
                </button>
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

            {/* Loading state */}
            {loading && (
                <div className="flex items-center justify-center py-12">
                    <Loader2 size={24} className="text-zinc-500 animate-spin" />
                </div>
            )}

            {/* Skills Grid */}
            {!loading && (
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
            )}

            {!loading && filteredSkills.length === 0 && (
                <div className="text-center py-12">
                    <p className="text-sm text-zinc-500">
                        {searchQuery ? `No skills found matching "${searchQuery}"` : 'No skills learned yet'}
                    </p>
                </div>
            )}
        </div>
    );
}
