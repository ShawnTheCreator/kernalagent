'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Activity, Sparkles, BarChart3, Settings } from 'lucide-react';

const navItems = [
    { href: '/dashboard', label: 'Home', icon: <LayoutDashboard size={20} /> },
    { href: '/dashboard/activity', label: 'Activity', icon: <Activity size={20} /> },
    { href: '/dashboard/skills', label: 'Skills', icon: <Sparkles size={20} /> },
    { href: '/dashboard/usage', label: 'Usage', icon: <BarChart3 size={20} /> },
    { href: '/dashboard/settings', label: 'Config', icon: <Settings size={20} /> },
];

export function MobileBottomNav() {
    const pathname = usePathname();

    return (
        <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-[#0A0A0A] border-t border-zinc-900" style={{ paddingBottom: 'env(safe-area-inset-bottom, 0)' }}>
            <div className="flex items-center justify-around h-16 px-2">
                {navItems.map((item) => {
                    const isActive = pathname === item.href ||
                        (item.href !== '/dashboard' && pathname.startsWith(item.href));

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`
                relative flex flex-col items-center justify-center gap-1 px-3 py-2 min-w-[56px] rounded-lg transition-colors
                ${isActive ? 'text-white' : 'text-zinc-600'}
              `}
                        >
                            {item.icon}
                            <span className="text-[9px] font-bold uppercase tracking-wider">{item.label}</span>

                            {isActive && (
                                <motion.div
                                    layoutId="mobile-nav-indicator"
                                    className="absolute top-0 left-1/2 -translate-x-1/2 w-6 h-0.5 bg-white rounded-full"
                                    transition={{ duration: 0.15 }}
                                />
                            )}
                        </Link>
                    );
                })}
            </div>
        </nav>
    );
}
