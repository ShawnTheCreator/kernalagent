'use client';

import { useEffect, useState } from 'react';
import { Activity, Search, Menu } from 'lucide-react';

interface TopBarProps {
    onMenuClick: () => void;
}

export function TopBar({ onMenuClick }: TopBarProps) {
    const [uptime, setUptime] = useState('00:00:00');
    const [startTime] = useState(() => Date.now());

    useEffect(() => {
        const timer = setInterval(() => {
            const diff = Date.now() - startTime;
            const h = Math.floor(diff / 3600000).toString().padStart(2, '0');
            const m = Math.floor((diff % 3600000) / 60000).toString().padStart(2, '0');
            const s = Math.floor((diff % 60000) / 1000).toString().padStart(2, '0');
            setUptime(`${h}:${m}:${s}`);
        }, 1000);
        return () => clearInterval(timer);
    }, [startTime]);

    return (
        <header className="h-16 md:h-20 bg-[#080808]/80 backdrop-blur-md border-b border-zinc-900 px-6 md:px-10 flex items-center justify-between z-40 sticky top-0">
            <div className="flex items-center gap-6">
                {/* Mobile menu button */}
                <button
                    onClick={onMenuClick}
                    className="lg:hidden p-2 -ml-2 text-zinc-400 hover:text-white"
                >
                    <Menu size={20} />
                </button>

                {/* System status */}
                <div className="hidden lg:flex items-center gap-2 text-zinc-500">
                    <Activity size={14} className="text-blue-500" />
                    <span className="text-[10px] font-black uppercase tracking-[0.2em]">System Normal</span>
                </div>

                <div className="h-4 w-px bg-zinc-800 hidden lg:block" />

                {/* Uptime */}
                <div className="flex flex-col">
                    <span className="text-[9px] font-bold text-zinc-600 uppercase tracking-widest">Active Runtime</span>
                    <span className="text-xs font-mono font-bold text-zinc-300">{uptime}</span>
                </div>
            </div>

            <div className="flex items-center gap-4">
                {/* Search */}
                <div className="relative hidden sm:block">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" size={14} />
                    <input
                        placeholder="EXECUTE COMMAND..."
                        className="bg-zinc-900/50 border border-zinc-800 rounded-lg py-2 pl-10 pr-4 text-[10px] font-bold tracking-widest focus:outline-none focus:border-zinc-600 w-48 lg:w-64 transition-all placeholder:text-zinc-600 text-white"
                    />
                </div>

                {/* Status indicator */}
                <div className="w-8 h-8 rounded-full border border-zinc-800 bg-zinc-900 flex items-center justify-center overflow-hidden">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                </div>
            </div>
        </header>
    );
}
