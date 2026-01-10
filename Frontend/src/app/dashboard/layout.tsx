'use client';

import { useState } from 'react';
import { SystemSidebar, TopBar, MobileBottomNav } from '@/components/dashboard/layout';

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
                <main className="flex-grow overflow-y-auto p-6 md:p-10 pb-24 lg:pb-10 custom-scrollbar">
                    <div className="max-w-6xl mx-auto">
                        {children}
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
