'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { SystemSidebar, TopBar, MobileBottomNav } from '@/components/dashboard/layout';
import { useAuth } from '@/contexts/AuthContext';

// HACKATHON: Set to true to bypass auth for demo
const DEV_BYPASS_AUTH = false; // DISABLED - Use real Firebase Auth

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const router = useRouter();
    const { user, loading } = useAuth();
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    useEffect(() => {
        // Skip auth check if bypass enabled OR still loading
        if (DEV_BYPASS_AUTH || loading) return;

        // Redirect to login if not authenticated
        if (!user) {
            router.push('/login');
        }
    }, [user, loading, router]);

    return (
        <div className="min-h-screen bg-[#080808] text-zinc-300 font-sans flex flex-col lg:flex-row">
            {/* Sidebar */}
            <SystemSidebar
                collapsed={sidebarCollapsed}
                onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
                mobileOpen={mobileMenuOpen}
                onMobileClose={() => setMobileMenuOpen(false)}
            />

            {/* Main Content Area */}
            <div className="flex-grow flex flex-col min-w-0">
                {/* Header */}
                <TopBar onMenuClick={() => setMobileMenuOpen(true)} />

                {/* Viewport */}
                <main className="flex-grow overflow-y-auto p-4 md:p-8 lg:p-10 pb-24 lg:pb-10 custom-scrollbar">
                    <div className="max-w-4xl lg:max-w-6xl 2xl:max-w-[1800px] mx-auto w-full transition-all duration-300">
                        {loading ? (
                            // Loading skeleton - shows immediately while auth state is being checked
                            <div className="space-y-10 animate-pulse">
                                {/* Header skeleton */}
                                <div className="space-y-2">
                                    <div className="h-8 w-48 bg-zinc-800/50 rounded-lg" />
                                    <div className="h-4 w-72 bg-zinc-900/50 rounded" />
                                </div>
                                {/* Metrics grid skeleton */}
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                                    {[...Array(4)].map((_, i) => (
                                        <div key={i} className="bg-zinc-900/40 border border-zinc-800 p-5 rounded-xl space-y-4">
                                            <div className="flex justify-between">
                                                <div className="w-10 h-10 bg-zinc-800/50 rounded-lg" />
                                                <div className="w-12 h-5 bg-zinc-800/30 rounded-full" />
                                            </div>
                                            <div>
                                                <div className="h-3 w-20 bg-zinc-800/40 rounded mb-2" />
                                                <div className="h-7 w-16 bg-zinc-800/50 rounded" />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                {/* Main content skeleton */}
                                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                                    <div className="lg:col-span-2 bg-zinc-950 border border-zinc-900 rounded-2xl p-6 h-[400px]">
                                        <div className="h-4 w-32 bg-zinc-800/50 rounded mb-6" />
                                        <div className="space-y-4">
                                            {[...Array(5)].map((_, i) => (
                                                <div key={i} className="flex items-center gap-4">
                                                    <div className="w-10 h-10 bg-zinc-800/30 rounded-lg" />
                                                    <div className="flex-1 space-y-2">
                                                        <div className="h-3 w-24 bg-zinc-800/40 rounded" />
                                                        <div className="h-4 w-3/4 bg-zinc-800/30 rounded" />
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="bg-zinc-950 border border-zinc-900 rounded-2xl p-6 h-[300px]">
                                        <div className="h-4 w-24 bg-zinc-800/50 rounded mb-6" />
                                        <div className="flex items-center gap-4 p-4 bg-zinc-900/50 rounded-xl">
                                            <div className="w-12 h-12 bg-zinc-800/50 rounded-xl" />
                                            <div className="space-y-2">
                                                <div className="h-4 w-24 bg-zinc-800/50 rounded" />
                                                <div className="h-3 w-16 bg-zinc-800/30 rounded" />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            children
                        )}
                    </div>
                </main>

                {/* Status Footer */}
                <footer className="hidden lg:flex h-10 border-t border-zinc-900 bg-black/40 px-6 md:px-10 items-center justify-between text-[9px] font-bold uppercase tracking-[0.3em] text-zinc-600">
                    <div className="flex gap-6">
                        <span className="text-blue-500/50">ENC: 0x2A991</span>
                        <span>Local Instance: OK</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/50 shadow-[0_0_8px_rgba(16,185,129,0.2)]" />
                        <span>Connection Secure</span>
                    </div>
                </footer>
            </div>

            {/* Mobile Bottom Nav */}
            <MobileBottomNav />

            <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #1a1a1a; border-radius: 10px; }
        @media (max-width: 768px) {
          .custom-scrollbar::-webkit-scrollbar { width: 0; }
        }
      `}</style>
        </div>
    );
}
