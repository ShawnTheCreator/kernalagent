'use client';

import { motion } from 'framer-motion';
import { SkillsList } from '@/components/dashboard/skills';

export default function SkillsPage() {
    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="space-y-6"
        >
            {/* Header */}
            <div>
                <h1 className="text-xl font-semibold text-white">Skills</h1>
                <p className="text-sm text-zinc-600 mt-1">Learned capabilities and confidence levels</p>
            </div>

            {/* Skills List */}
            <SkillsList />
        </motion.div>
    );
}
