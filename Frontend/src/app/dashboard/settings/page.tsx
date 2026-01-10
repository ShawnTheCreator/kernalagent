'use client';

import { motion } from 'framer-motion';
import { Lock, Shield, Cpu, Database } from 'lucide-react';

// Setting Row Component
function SettingRow({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex justify-between items-center py-4 border-b border-zinc-900">
            <span className="text-xs font-bold text-zinc-400">{label}</span>
            <span className="text-xs font-mono font-bold text-white">{value}</span>
        </div>
    );
}

// Section Component
function SettingsSection({
    icon: Icon,
    title,
    color = 'text-blue-500',
    children
}: {
    icon: React.ComponentType<{ size?: number; className?: string }>;
    title: string;
    color?: string;
    children: React.ReactNode;
}) {
    return (
        <section className="space-y-6">
            <div className={`flex items-center gap-2 ${color} mb-4`}>
                <Icon size={16} />
                <span className="text-[11px] font-black uppercase tracking-widest">{title}</span>
            </div>
            {children}
        </section>
    );
}

export default function SettingsPage() {
    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
            className="max-w-2xl space-y-10"
        >
            {/* Header */}
            <div>
                <h1 className="text-2xl font-black text-white tracking-tighter uppercase mb-2">Core Calibration</h1>
                <p className="text-zinc-500 text-sm">Adjust underlying architectural parameters for the Ghost engine.</p>
            </div>

            {/* Settings Sections */}
            <div className="space-y-10">
                <SettingsSection icon={Lock} title="Access Control">
                    <SettingRow label="API Throttling" value="Automatic" />
                    <SettingRow label="Multi-threaded Logic" value="Enabled" />
                    <SettingRow label="Data Encryption" value="AES-256" />
                </SettingsSection>

                <SettingsSection icon={Shield} title="Security" color="text-emerald-500">
                    <SettingRow label="Firewall Status" value="Active" />
                    <SettingRow label="Intrusion Detection" value="Passive Mode" />
                    <SettingRow label="Auth Protocol" value="OAuth 2.0" />
                </SettingsSection>

                <SettingsSection icon={Cpu} title="Performance" color="text-amber-500">
                    <SettingRow label="CPU Priority" value="High" />
                    <SettingRow label="Memory Limit" value="8GB" />
                    <SettingRow label="Process Threads" value="16" />
                </SettingsSection>

                <SettingsSection icon={Database} title="Storage" color="text-violet-500">
                    <SettingRow label="Cache Strategy" value="LRU" />
                    <SettingRow label="Backup Frequency" value="Hourly" />
                    <SettingRow label="Data Retention" value="30 Days" />
                </SettingsSection>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4 pt-6 border-t border-zinc-900">
                <button className="flex-1 py-3 bg-zinc-900 rounded-xl text-[10px] font-black uppercase tracking-widest text-zinc-400 hover:text-white border border-zinc-800 transition-all">
                    Reset Defaults
                </button>
                <button className="flex-1 py-3 bg-white text-black rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-blue-600 hover:text-white transition-all">
                    Apply Changes
                </button>
            </div>
        </motion.div>
    );
}
