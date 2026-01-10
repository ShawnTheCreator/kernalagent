'use client';

import { motion } from 'framer-motion';
import { Moon, Send, Eye, Gauge } from 'lucide-react';
import { useDashboardStore } from '@/stores/dashboardStore';

interface ToggleProps {
    label: string;
    description: string;
    checked: boolean;
    onChange: (checked: boolean) => void;
    icon: React.ReactNode;
}

function Toggle({ label, description, checked, onChange, icon }: ToggleProps) {
    return (
        <div className="flex items-center justify-between py-4 border-b border-white/[0.05]">
            <div className="flex items-start gap-3">
                <div className="text-zinc-500 mt-0.5">{icon}</div>
                <div>
                    <div className="text-sm font-medium text-white">{label}</div>
                    <div className="text-xs text-zinc-600 mt-0.5">{description}</div>
                </div>
            </div>
            <button
                onClick={() => onChange(!checked)}
                className={`relative w-10 h-6 rounded-full transition-colors ${checked ? 'bg-white' : 'bg-zinc-800'}`}
                role="switch"
                aria-checked={checked}
            >
                <motion.div
                    animate={{ x: checked ? 16 : 2 }}
                    transition={{ duration: 0.15, ease: 'easeOut' }}
                    className={`absolute top-1 w-4 h-4 rounded-full ${checked ? 'bg-black' : 'bg-zinc-500'}`}
                />
            </button>
        </div>
    );
}

interface SliderProps {
    label: string;
    description: string;
    value: number;
    onChange: (value: number) => void;
    icon: React.ReactNode;
    min?: number;
    max?: number;
    leftLabel?: string;
    rightLabel?: string;
}

function Slider({ label, description, value, onChange, icon, min = 0, max = 100, leftLabel, rightLabel }: SliderProps) {
    return (
        <div className="py-4 border-b border-white/[0.05]">
            <div className="flex items-start gap-3 mb-3">
                <div className="text-zinc-500 mt-0.5">{icon}</div>
                <div className="flex-1">
                    <div className="flex items-center justify-between">
                        <div className="text-sm font-medium text-white">{label}</div>
                        <div className="text-xs font-mono text-zinc-500">{value}%</div>
                    </div>
                    <div className="text-xs text-zinc-600 mt-0.5">{description}</div>
                </div>
            </div>
            <div className="pl-7">
                <input
                    type="range"
                    min={min}
                    max={max}
                    value={value}
                    onChange={(e) => onChange(Number(e.target.value))}
                    className="w-full h-1 bg-zinc-800 rounded-full appearance-none cursor-pointer accent-white"
                />
                {(leftLabel || rightLabel) && (
                    <div className="flex justify-between text-[10px] text-zinc-600 mt-1">
                        <span>{leftLabel}</span>
                        <span>{rightLabel}</span>
                    </div>
                )}
            </div>
        </div>
    );
}

export function SettingsForm() {
    const {
        telemetryEnabled,
        visionSensitivity,
        executionSpeed,
        updateSettings
    } = useDashboardStore();

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="space-y-6"
        >
            {/* Appearance */}
            <div className="bg-[#0a0a0a] border border-white/[0.05] rounded-xl p-4">
                <h3 className="text-[10px] uppercase tracking-widest text-zinc-600 mb-2">Appearance</h3>
                <Toggle
                    label="Dark Mode"
                    description="Use dark theme (default)"
                    checked={true}
                    onChange={() => { }}
                    icon={<Moon size={16} />}
                />
            </div>

            {/* Privacy */}
            <div className="bg-[#0a0a0a] border border-white/[0.05] rounded-xl p-4">
                <h3 className="text-[10px] uppercase tracking-widest text-zinc-600 mb-2">Privacy</h3>
                <Toggle
                    label="Telemetry"
                    description="Send anonymous usage data to improve the agent"
                    checked={telemetryEnabled}
                    onChange={(checked) => updateSettings({ telemetryEnabled: checked })}
                    icon={<Send size={16} />}
                />
            </div>

            {/* Agent Behavior */}
            <div className="bg-[#0a0a0a] border border-white/[0.05] rounded-xl p-4">
                <h3 className="text-[10px] uppercase tracking-widest text-zinc-600 mb-2">Agent Behavior</h3>
                <Slider
                    label="Vision Sensitivity"
                    description="How aggressively the agent captures screen state"
                    value={visionSensitivity}
                    onChange={(value) => updateSettings({ visionSensitivity: value })}
                    icon={<Eye size={16} />}
                    leftLabel="Conservative"
                    rightLabel="Aggressive"
                />
                <Slider
                    label="Execution Speed"
                    description="Trade off between speed and safety"
                    value={executionSpeed}
                    onChange={(value) => updateSettings({ executionSpeed: value })}
                    icon={<Gauge size={16} />}
                    leftLabel="Safe"
                    rightLabel="Fast"
                />
            </div>
        </motion.div>
    );
}
