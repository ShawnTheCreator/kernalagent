'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
    Settings, Globe, Zap, Cpu, Shield, LogOut,
    Check, AlertTriangle, User, Bell, Lock
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
    description,
    children
}: {
    icon: React.ComponentType<{ size?: number; className?: string }>;
    title: string;
    description?: string;
    children: React.ReactNode;
}) {
    return (
        <section className="group bg-[#0A0A0A] border border-zinc-900/50 hover:border-zinc-800 rounded-2xl p-6 transition-all duration-300">
            <div className="flex items-center gap-3 mb-6">
                <div className="p-2.5 bg-zinc-900 rounded-xl text-zinc-400 group-hover:text-white group-hover:bg-zinc-800 transition-colors">
                    <Icon size={20} />
                </div>
                <div>
                    <h3 className="text-sm font-bold text-zinc-100 uppercase tracking-wide">{title}</h3>
                    {description && <p className="text-xs text-zinc-500 mt-1">{description}</p>}
                </div>
            </div>
            <div className="space-y-1 pl-1">
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
        <div className="flex justify-between items-center py-4 border-b border-dashed border-zinc-900 last:border-0 hover:bg-zinc-900/30 -mx-2 px-2 rounded-lg transition-colors">
            <div>
                <span className="text-sm font-medium text-zinc-300">{label}</span>
                {description && <p className="text-xs text-zinc-600 mt-0.5">{description}</p>}
            </div>
            <button
                onClick={() => !disabled && onChange(!checked)}
                disabled={disabled}
                className={`relative w-11 h-6 rounded-full transition-all duration-300 ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                    } ${checked ? 'bg-white shadow-[0_0_10px_rgba(255,255,255,0.3)]' : 'bg-zinc-800'}`}
                role="switch"
                aria-checked={checked}
            >
                <motion.div
                    animate={{ x: checked ? 22 : 2 }}
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                    className={`absolute top-1 w-4 h-4 rounded-full shadow-sm ${checked ? 'bg-black' : 'bg-zinc-400'}`}
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
        <div className="flex justify-between items-center py-4 border-b border-dashed border-zinc-900 last:border-0 hover:bg-zinc-900/30 -mx-2 px-2 rounded-lg transition-colors">
            <div>
                <span className="text-sm font-medium text-zinc-300">{label}</span>
                {description && <p className="text-xs text-zinc-600 mt-0.5">{description}</p>}
            </div>
            <div className="relative">
                <select
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    disabled={disabled}
                    className={`appearance-none bg-zinc-900 border border-zinc-800 hover:border-zinc-700 rounded-lg pl-3 pr-8 py-1.5 text-xs font-mono text-zinc-300 focus:outline-none focus:ring-1 focus:ring-white/20 transition-colors ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                >
                    {options.map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                    ))}
                </select>
                <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-500">
                    <svg width="10" height="6" viewBox="0 0 10 6" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                </div>
            </div>
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
        <div className="flex justify-between items-center py-4 border-b border-dashed border-zinc-900 last:border-0 hover:bg-zinc-900/30 -mx-2 px-2 rounded-lg transition-colors">
            <div>
                <span className="text-sm font-medium text-zinc-300">{label}</span>
                {description && <p className="text-xs text-zinc-600 mt-0.5">{description}</p>}
            </div>
            <input
                type="number"
                value={value}
                onChange={(e) => onChange(Number(e.target.value))}
                min={min}
                max={max}
                className="w-20 bg-zinc-900 border border-zinc-800 hover:border-zinc-700 rounded-lg px-3 py-1.5 text-xs font-mono text-white text-center focus:outline-none focus:ring-1 focus:ring-white/20 transition-colors"
            />
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

    // Logout - correctly uses Firebase context
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
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            className="max-w-4xl mx-auto pb-20"
        >
            {/* Page Header */}
            <div className="mb-10 flex items-end justify-between">
                <div>
                    <h1 className="text-3xl font-black text-white tracking-tight uppercase mb-2 flex items-center gap-3">
                        <Settings className="text-zinc-500" size={24} />
                        Settings
                    </h1>
                    <p className="text-zinc-500 font-medium">Manage your agent preferences and account security</p>
                </div>

                {/* Profile Badge */}
                <Link href="/dashboard/profile" className="hidden md:flex items-center gap-3 bg-zinc-900/50 border border-zinc-800 pr-5 pl-2 py-2 rounded-full hover:bg-zinc-800 hover:border-zinc-700 transition-all cursor-pointer group">
                    <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-400 border border-zinc-700 overflow-hidden group-hover:border-zinc-500 transition-colors">
                        {user?.photoURL ? (
                            <img src={user.photoURL} alt="User" className="w-full h-full object-cover" />
                        ) : (
                            <User size={14} />
                        )}
                    </div>
                    <div className="flex flex-col">
                        <span className="text-xs font-bold text-zinc-300 group-hover:text-white transition-colors">{user?.displayName || 'Ghost User'}</span>
                        <span className="text-[10px] text-zinc-600 font-mono group-hover:text-zinc-500 transition-colors">{user?.email}</span>
                    </div>
                </Link>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* Left Column */}
                <div className="space-y-6">
                    {/* ✅ General Settings */}
                    <SettingsSection icon={Globe} title="General" description="Language and system preferences">
                        <SelectRow
                            label="Language"
                            value={settings.language}
                            options={['English', 'Spanish', 'French', 'German', 'Japanese']}
                            onChange={(v) => updateSetting('language', v)}
                        />
                        <ToggleRow
                            label="Auto-start Agent"
                            description="Launch automatically on system login"
                            checked={settings.autoStart}
                            onChange={(v) => updateSetting('autoStart', v)}
                        />
                    </SettingsSection>

                    {/* ✅ Agent Behavior */}
                    <SettingsSection icon={Zap} title="Agent Behavior" description="How the agent interacts with your system">
                        <SelectRow
                            label="Execution Mode"
                            description="MOCK = Test mode, REAL = Live actions"
                            value={settings.executionMode}
                            options={['MOCK', 'REAL']}
                            onChange={(v) => updateSetting('executionMode', v as 'MOCK' | 'REAL')}
                        />
                        <ToggleRow
                            label="Confirm Before Actions"
                            description="Require approval for critical steps"
                            checked={settings.confirmActions}
                            onChange={(v) => updateSetting('confirmActions', v)}
                        />
                        <NumberRow
                            label="Max Actions Session"
                            description="Safe limit per automation run"
                            value={settings.maxActionsPerSession}
                            onChange={(v) => updateSetting('maxActionsPerSession', v)}
                            min={10}
                            max={200}
                        />
                    </SettingsSection>
                </div>

                {/* Right Column */}
                <div className="space-y-6">
                    {/* ✅ Performance */}
                    <SettingsSection icon={Cpu} title="Performance" description="System resource allocation">
                        <SelectRow
                            label="CPU Priority"
                            value={settings.cpuPriority}
                            options={['Low', 'Medium', 'High']}
                            onChange={(v) => updateSetting('cpuPriority', v as 'Low' | 'Medium' | 'High')}
                        />
                        <div className="flex justify-between items-center py-4 border-b border-dashed border-zinc-900">
                            <span className="text-sm font-medium text-zinc-300">Max Memory</span>
                            <span className="text-xs font-mono bg-zinc-900 border border-zinc-800 px-2 py-1 rounded text-zinc-400">8 GB (AUTO)</span>
                        </div>
                    </SettingsSection>

                    {/* ✅ Account & Security */}
                    <SettingsSection icon={Shield} title="Account & Security" description="Manage your session and access">
                        <div className="flex justify-between items-center py-4 border-b border-dashed border-zinc-900">
                            <div className="flex items-center gap-2">
                                <Lock size={14} className="text-emerald-500" />
                                <span className="text-sm font-medium text-zinc-300">Auth Status</span>
                            </div>
                            <span className="text-xs font-bold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 px-2 py-1 rounded uppercase tracking-wider">
                                {user ? 'Authenticated' : 'Offline'}
                            </span>
                        </div>

                        {/* Logout Area */}
                        <div className="mt-6 pt-2">
                            {!showLogoutConfirm ? (
                                <button
                                    onClick={() => setShowLogoutConfirm(true)}
                                    className="w-full flex items-center justify-center gap-2 py-3 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-red-900/50 rounded-xl text-zinc-400 hover:text-red-400 text-xs font-bold uppercase tracking-widest transition-all duration-300 group"
                                >
                                    <LogOut size={16} className="group-hover:-translate-x-1 transition-transform" />
                                    Sign Out
                                </button>
                            ) : (
                                <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-4 animate-in fade-in slide-in-from-top-2 duration-200">
                                    <div className="flex items-center gap-3 text-red-200 text-sm font-medium mb-4">
                                        <AlertTriangle size={16} className="text-red-500" />
                                        <span>Confirm logout?</span>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => setShowLogoutConfirm(false)}
                                            className="flex-1 py-2 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-lg text-xs font-bold uppercase tracking-wider text-zinc-400 hover:text-white transition-colors"
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            onClick={handleLogout}
                                            className="flex-1 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-xs font-bold uppercase tracking-wider text-white shadow-lg shadow-red-900/20 transition-all hover:scale-[1.02]"
                                        >
                                            Logout
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </SettingsSection>
                </div>
            </div>

            {/* Bottom Action Bar */}
            <motion.div
                className="fixed bottom-0 left-0 right-0 lg:left-72 bg-[#0A0A0A]/80 backdrop-blur-md border-t border-zinc-900 p-6 z-40"
                initial={{ y: 100 }}
                animate={{ y: 0 }}
                transition={{ delay: 0.2 }}
            >
                <div className="max-w-4xl mx-auto flex items-center justify-between gap-4">
                    <button
                        onClick={handleResetDefaults}
                        className="text-xs font-bold uppercase tracking-wider text-zinc-500 hover:text-zinc-300 transition-colors"
                    >
                        Reset Defaults
                    </button>
                    <button
                        onClick={handleApplyChanges}
                        className="px-8 py-3 bg-white hover:bg-zinc-200 text-black rounded-full text-xs font-black uppercase tracking-widest transition-all hover:shadow-[0_0_20px_rgba(255,255,255,0.2)] flex items-center gap-2 transform active:scale-95"
                    >
                        {saveStatus === 'saved' ? (
                            <>
                                <Check size={16} className="text-emerald-600" />
                                <span>Changes Saved</span>
                            </>
                        ) : (
                            <span>Save Changes</span>
                        )}
                    </button>
                </div>
            </motion.div>
        </motion.div>
    );
}
