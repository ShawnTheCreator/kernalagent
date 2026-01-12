'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
    Settings, Globe, Zap, Cpu, Shield, LogOut,
    Check, AlertTriangle
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

// =============================================================================
// SETTINGS STORAGE HELPER
// =============================================================================

const SETTINGS_KEY = 'kernel_settings';

interface KernelSettings {
    // General
    language: string;
    autoStart: boolean;
    // Agent Behavior
    executionMode: 'MOCK' | 'REAL';
    confirmActions: boolean;
    maxActionsPerSession: number;
    // Performance (read-only for now)
    cpuPriority: 'Low' | 'Medium' | 'High';
}

const DEFAULT_SETTINGS: KernelSettings = {
    language: 'English',
    autoStart: false,
    executionMode: 'MOCK',
    confirmActions: true,
    maxActionsPerSession: 50,
    cpuPriority: 'Medium',
};

function loadSettings(): KernelSettings {
    if (typeof window === 'undefined') return DEFAULT_SETTINGS;
    try {
        const stored = localStorage.getItem(SETTINGS_KEY);
        if (stored) {
            return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
        }
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
    return DEFAULT_SETTINGS;
}

function saveSettings(settings: KernelSettings): void {
    try {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    } catch (e) {
        console.error('Failed to save settings:', e);
    }
}

// =============================================================================
// UI COMPONENTS
// =============================================================================

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
        <section className="bg-zinc-950 border border-zinc-800 rounded-xl p-5">
            <div className={`flex items-center gap-2 ${color} mb-4`}>
                <Icon size={16} />
                <span className="text-[11px] font-black uppercase tracking-widest">{title}</span>
            </div>
            <div className="space-y-1">
                {children}
            </div>
        </section>
    );
}

function ToggleRow({
    label,
    description,
    checked,
    onChange,
    disabled = false
}: {
    label: string;
    description?: string;
    checked: boolean;
    onChange: (checked: boolean) => void;
    disabled?: boolean;
}) {
    return (
        <div className="flex justify-between items-center py-3 border-b border-zinc-900 last:border-0">
            <div>
                <span className="text-sm font-medium text-white">{label}</span>
                {description && <p className="text-xs text-zinc-500 mt-0.5">{description}</p>}
            </div>
            <button
                onClick={() => !disabled && onChange(!checked)}
                disabled={disabled}
                className={`relative w-10 h-6 rounded-full transition-colors ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                    } ${checked ? 'bg-emerald-500' : 'bg-zinc-700'}`}
                role="switch"
                aria-checked={checked}
            >
                <motion.div
                    animate={{ x: checked ? 16 : 2 }}
                    transition={{ duration: 0.15, ease: 'easeOut' }}
                    className="absolute top-1 w-4 h-4 rounded-full bg-white"
                />
            </button>
        </div>
    );
}

function SelectRow({
    label,
    description,
    value,
    options,
    onChange,
    disabled = false
}: {
    label: string;
    description?: string;
    value: string;
    options: string[];
    onChange: (value: string) => void;
    disabled?: boolean;
}) {
    return (
        <div className="flex justify-between items-center py-3 border-b border-zinc-900 last:border-0">
            <div>
                <span className="text-sm font-medium text-white">{label}</span>
                {description && <p className="text-xs text-zinc-500 mt-0.5">{description}</p>}
            </div>
            <select
                value={value}
                onChange={(e) => onChange(e.target.value)}
                disabled={disabled}
                className={`bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-white ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                    }`}
            >
                {options.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                ))}
            </select>
        </div>
    );
}

function NumberRow({
    label,
    description,
    value,
    onChange,
    min = 1,
    max = 100
}: {
    label: string;
    description?: string;
    value: number;
    onChange: (value: number) => void;
    min?: number;
    max?: number;
}) {
    return (
        <div className="flex justify-between items-center py-3 border-b border-zinc-900 last:border-0">
            <div>
                <span className="text-sm font-medium text-white">{label}</span>
                {description && <p className="text-xs text-zinc-500 mt-0.5">{description}</p>}
            </div>
            <input
                type="number"
                value={value}
                onChange={(e) => onChange(Number(e.target.value))}
                min={min}
                max={max}
                className="w-20 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-white text-center"
            />
        </div>
    );
}

function ReadOnlyRow({
    label,
    value
}: {
    label: string;
    value: string;
}) {
    return (
        <div className="flex justify-between items-center py-3 border-b border-zinc-900 last:border-0">
            <span className="text-sm font-medium text-white">{label}</span>
            <span className="text-sm text-zinc-400 font-mono">{value}</span>
        </div>
    );
}

// =============================================================================
// MAIN SETTINGS PAGE
// =============================================================================

export default function SettingsPage() {
    const router = useRouter();
    const { logout, user } = useAuth();
    const [settings, setSettings] = useState<KernelSettings>(DEFAULT_SETTINGS);
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saved' | 'error'>('idle');
    const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

    // Load settings on mount
    useEffect(() => {
        setSettings(loadSettings());
    }, []);

    // Update a single setting
    const updateSetting = <K extends keyof KernelSettings>(key: K, value: KernelSettings[K]) => {
        setSettings((prev) => ({ ...prev, [key]: value }));
        setSaveStatus('idle'); // Mark as unsaved
    };

    // Apply changes (save to localStorage)
    const handleApplyChanges = () => {
        saveSettings(settings);
        setSaveStatus('saved');
        setTimeout(() => setSaveStatus('idle'), 2000);
    };

    // Reset to defaults
    const handleResetDefaults = () => {
        setSettings(DEFAULT_SETTINGS);
        saveSettings(DEFAULT_SETTINGS);
        setSaveStatus('saved');
        setTimeout(() => setSaveStatus('idle'), 2000);
    };

    // Logout - uses Firebase auth
    const handleLogout = async () => {
        try {
            await logout();
            router.push('/login');
        } catch (error) {
            console.error('Logout failed:', error);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
            className="max-w-2xl space-y-8"
        >
            {/* Header */}
            <div>
                <h1 className="text-2xl font-black text-white tracking-tighter uppercase mb-2">Settings</h1>
                <p className="text-zinc-500 text-sm">Configure your Kernel Agent preferences.</p>
            </div>

            {/* Settings Sections */}
            <div className="space-y-6">

                {/* ✅ General Settings */}
                <SettingsSection icon={Globe} title="General">
                    <SelectRow
                        label="Language"
                        value={settings.language}
                        options={['English', 'Spanish', 'French', 'German', 'Japanese']}
                        onChange={(v) => updateSetting('language', v)}
                    />
                    <ToggleRow
                        label="Auto-start Agent"
                        description="Start agent automatically on login"
                        checked={settings.autoStart}
                        onChange={(v) => updateSetting('autoStart', v)}
                    />
                </SettingsSection>

                {/* ✅ Agent Behavior */}
                <SettingsSection icon={Zap} title="Agent Behavior" color="text-amber-500">
                    <SelectRow
                        label="Execution Mode"
                        description="MOCK = preview only, REAL = live execution"
                        value={settings.executionMode}
                        options={['MOCK', 'REAL']}
                        onChange={(v) => updateSetting('executionMode', v as 'MOCK' | 'REAL')}
                    />
                    <ToggleRow
                        label="Confirm Before Actions"
                        description="Ask for confirmation before executing actions"
                        checked={settings.confirmActions}
                        onChange={(v) => updateSetting('confirmActions', v)}
                    />
                    <NumberRow
                        label="Max Actions Per Session"
                        description="Safety limit for automated actions"
                        value={settings.maxActionsPerSession}
                        onChange={(v) => updateSetting('maxActionsPerSession', v)}
                        min={10}
                        max={200}
                    />
                </SettingsSection>

                {/* ✅ Performance (mostly read-only) */}
                <SettingsSection icon={Cpu} title="Performance" color="text-blue-500">
                    <SelectRow
                        label="CPU Priority"
                        value={settings.cpuPriority}
                        options={['Low', 'Medium', 'High']}
                        onChange={(v) => updateSetting('cpuPriority', v as 'Low' | 'Medium' | 'High')}
                    />
                    {/* Read-only system values */}
                    <ReadOnlyRow label="Max Memory" value="8 GB (system)" />
                    <ReadOnlyRow label="Thread Count" value="16 (auto)" />
                </SettingsSection>

                {/* ✅ Security */}
                <SettingsSection icon={Shield} title="Security" color="text-emerald-500">
                    <ReadOnlyRow label="Auth Provider" value="Local (Firebase pending)" />
                    <ReadOnlyRow label="Data Encryption" value="AES-256" />

                    {/* Logout Button */}
                    <div className="pt-4 mt-4 border-t border-zinc-800">
                        {!showLogoutConfirm ? (
                            <button
                                onClick={() => setShowLogoutConfirm(true)}
                                className="w-full flex items-center justify-center gap-2 py-3 bg-red-950 hover:bg-red-900 border border-red-800 rounded-xl text-red-400 hover:text-red-300 text-sm font-bold uppercase tracking-wider transition-all"
                            >
                                <LogOut size={16} />
                                Logout
                            </button>
                        ) : (
                            <div className="space-y-3">
                                <div className="flex items-center gap-2 text-amber-400 text-sm">
                                    <AlertTriangle size={16} />
                                    <span>Are you sure you want to logout?</span>
                                </div>
                                <div className="flex gap-3">
                                    <button
                                        onClick={() => setShowLogoutConfirm(false)}
                                        className="flex-1 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm text-zinc-300 transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleLogout}
                                        className="flex-1 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-sm text-white font-bold transition-colors"
                                    >
                                        Yes, Logout
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </SettingsSection>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4 pt-6 border-t border-zinc-800">
                <button
                    onClick={handleResetDefaults}
                    className="flex-1 py-3 bg-zinc-900 rounded-xl text-[10px] font-black uppercase tracking-widest text-zinc-400 hover:text-white border border-zinc-800 transition-all"
                >
                    Reset Defaults
                </button>
                <button
                    onClick={handleApplyChanges}
                    className="flex-1 py-3 bg-white text-black rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-emerald-500 hover:text-white transition-all flex items-center justify-center gap-2"
                >
                    {saveStatus === 'saved' ? (
                        <>
                            <Check size={14} />
                            Saved!
                        </>
                    ) : (
                        'Apply Changes'
                    )}
                </button>
            </div>
        </motion.div>
    );
}
