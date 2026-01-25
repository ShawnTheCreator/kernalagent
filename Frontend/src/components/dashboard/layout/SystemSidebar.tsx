'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LayoutDashboard,
    Activity,
    Sparkles,
    BarChart3,
    Settings,
    X,
    ChevronLeft,
    ChevronRight,
    LogOut,
    User,
    HelpCircle
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

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
    // Settings moved to user dropdown
];

interface SystemSidebarProps {
    collapsed: boolean;
    onToggle: () => void;
    mobileOpen: boolean;
    onMobileClose: () => void;
}

export function SystemSidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SystemSidebarProps) {
    const pathname = usePathname();
    const { user, logout } = useAuth();
    const [profileOpen, setProfileOpen] = useState(false);
    const profileRef = useRef<HTMLDivElement>(null);

    // Close profile dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
                setProfileOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    // Helper for initials
    const getInitials = () => {
        if (user?.displayName) {
            return user.displayName.substring(0, 2).toUpperCase();
        }
        return 'US';
    };

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

                {/* User Profile Section (Bottom) */}
                <div className="p-4 border-t border-zinc-900 relative" ref={profileRef}>
                    <AnimatePresence>
                        {profileOpen && (
                            <motion.div
                                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                                transition={{ duration: 0.1 }}
                                className="absolute bottom-full left-4 right-4 mb-2 bg-[#1A1A1A] border border-zinc-800 rounded-xl overflow-hidden shadow-xl z-50"
                                style={{ width: collapsed ? '200px' : 'auto', left: collapsed ? '0' : '16px' }}
                            >
                                <div className="p-1">
                                    <Link
                                        href="/dashboard/profile"
                                        className="flex items-center gap-3 px-3 py-2 text-sm text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors w-full"
                                        onClick={() => setProfileOpen(false)}
                                    >
                                        <User size={16} />
                                        <span>Profile</span>
                                    </Link>
                                    <Link
                                        href="/dashboard/settings"
                                        className="flex items-center gap-3 px-3 py-2 text-sm text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors w-full"
                                        onClick={() => setProfileOpen(false)}
                                    >
                                        <Settings size={16} />
                                        <span>Settings</span>
                                    </Link>
                                    <button className="flex items-center gap-3 px-3 py-2 text-sm text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors w-full text-left">
                                        <HelpCircle size={16} />
                                        <span>Help & FAQ</span>
                                    </button>
                                    <div className="h-px bg-zinc-800 my-1" />
                                    <button
                                        onClick={() => logout()}
                                        className="flex items-center gap-3 px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors w-full text-left"
                                    >
                                        <LogOut size={16} />
                                        <span>Log out</span>
                                    </button>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <button
                        onClick={() => setProfileOpen(!profileOpen)}
                        className={`w-full flex items-center gap-3 p-2 rounded-xl border border-transparent hover:bg-zinc-900 transition-colors ${profileOpen ? 'bg-zinc-900 border-zinc-800' : ''}`}
                    >
                        <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-400 shrink-0 border border-zinc-700 overflow-hidden relative">
                            {user?.photoURL ? (
                                <img src={user.photoURL} alt="User" className="w-full h-full object-cover" />
                            ) : (
                                <span className="text-xs font-bold">{getInitials()}</span>
                            )}
                        </div>

                        {!collapsed && (
                            <div className="flex flex-col items-start overflow-hidden">
                                <span className="text-sm font-medium text-zinc-200 truncate w-full">
                                    {user?.displayName || 'Ghost User'}
                                </span>
                                <span className="text-[10px] text-zinc-500 truncate w-full">
                                    {user?.email || 'user@example.com'}
                                </span>
                            </div>
                        )}
                    </button>
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
