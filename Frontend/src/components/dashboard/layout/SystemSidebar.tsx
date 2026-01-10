'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LayoutDashboard,
    Activity,
    Sparkles,
    BarChart3,
    Settings,
    Shield,
    X,
    ChevronLeft,
    ChevronRight
} from 'lucide-react';

interface NavItem {
    href: string;
    label: string;
    icon: React.ReactNode;
}

const navItems: NavItem[] = [
    { href: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={16} /> },
    { href: '/dashboard/activity', label: 'Activity', icon: <Activity size={16} /> },
    { href: '/dashboard/skills', label: 'Skills', icon: <Sparkles size={16} /> },
    { href: '/dashboard/usage', label: 'Usage', icon: <BarChart3 size={16} /> },
    { href: '/dashboard/settings', label: 'Settings', icon: <Settings size={16} /> },
];

interface SystemSidebarProps {
    collapsed: boolean;
    onToggle: () => void;
    mobileOpen: boolean;
    onMobileClose: () => void;
}

export function SystemSidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SystemSidebarProps) {
    const pathname = usePathname();

    return (
        <>
            {/* Mobile overlay */}
            {mobileOpen && (
                <div
                    className="fixed inset-0 bg-black/60 z-40 lg:hidden"
                    onClick={onMobileClose}
                />
            )}

            <motion.aside
                initial={false}
                animate={{
                    width: collapsed ? 72 : 256
                }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                className={`
          fixed lg:relative inset-y-0 left-0 z-50
          bg-[#0A0A0A] border-r border-zinc-900 flex flex-col
          transition-transform duration-300
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
            >
                {/* Logo */}
                <div className="h-20 p-6 flex items-center justify-between border-b border-zinc-900">
                    <Link href="/dashboard" className="flex items-center gap-3">
                        <div className="w-6 h-6 bg-white rounded flex items-center justify-center">
                            <div className="w-2 h-2 bg-black rounded-sm" />
                        </div>
                        {!collapsed && (
                            <motion.span
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="font-black text-xl tracking-tighter uppercase text-white"
                            >
                                Kernel
                            </motion.span>
                        )}
                    </Link>
                    <button
                        onClick={onMobileClose}
                        className="lg:hidden p-2 text-zinc-500 hover:text-white"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Navigation */}
                <nav className="flex-grow p-4 space-y-1">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href ||
                            (item.href !== '/dashboard' && pathname.startsWith(item.href));

                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                onClick={onMobileClose}
                                className={`
                  w-full flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 group
                  ${isActive
                                        ? 'bg-zinc-100 text-zinc-950 shadow-sm'
                                        : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900'
                                    }
                `}
                            >
                                <span className={`${isActive ? '' : 'group-hover:scale-110 transition-transform'}`}>
                                    {item.icon}
                                </span>
                                {!collapsed && (
                                    <span className="text-[11px] font-bold uppercase tracking-wider">
                                        {item.label}
                                    </span>
                                )}
                            </Link>
                        );
                    })}
                </nav>

                {/* Version Info */}
                <div className="p-4 border-t border-zinc-900">
                    <div className={`flex items-center gap-3 p-3 bg-zinc-900/50 rounded-xl border border-zinc-800 ${collapsed ? 'justify-center' : ''}`}>
                        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shrink-0">
                            <Shield size={16} />
                        </div>
                        {!collapsed && (
                            <div className="flex flex-col">
                                <span className="text-[10px] font-black uppercase text-zinc-400">Core Safe</span>
                                <span className="text-[9px] font-mono text-zinc-600">V.1.0.4-STABLE</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Collapse Toggle (Desktop only) */}
                <div className="hidden lg:block p-2 border-t border-zinc-900">
                    <button
                        onClick={onToggle}
                        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-zinc-600 hover:text-zinc-300 hover:bg-zinc-900 transition-colors"
                    >
                        {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
                    </button>
                </div>
            </motion.aside>
        </>
    );
}
