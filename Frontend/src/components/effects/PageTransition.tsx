'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';

// Loading animation keyframes defined in globals.css
export function PageTransitionProvider({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const [isTransitioning, setIsTransitioning] = useState(false);
    const [displayedChildren, setDisplayedChildren] = useState(children);

    useEffect(() => {
        setIsTransitioning(true);
        const timer = setTimeout(() => {
            setDisplayedChildren(children);
            setIsTransitioning(false);
        }, 600);
        return () => clearTimeout(timer);
    }, [pathname, children]);

    return (
        <>
            <PageTransition isVisible={isTransitioning} />
            {displayedChildren}
        </>
    );
}

function PageTransition({ isVisible }: { isVisible: boolean }) {
    if (!isVisible) return null;

    return (
        <div className="fixed inset-0 z-[100] bg-kernel-bg flex flex-col items-center justify-center">
            {/* Background Pattern */}
            <div
                className="absolute inset-0 opacity-[0.02] pointer-events-none"
                style={{
                    backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)',
                    backgroundSize: '60px 60px'
                }}
            />

            {/* Animated Logo */}
            <div className="relative">
                {/* Outer Ring */}
                <div className="absolute -inset-8 border border-white/10 rounded-full animate-[spin_4s_linear_infinite]" />
                <div className="absolute -inset-12 border border-white/5 rounded-full animate-[spin_6s_linear_infinite_reverse]" />

                {/* Glow */}
                <div className="absolute -inset-4 bg-white/5 rounded-full blur-xl animate-pulse" />

                {/* Logo */}
                <div className="relative w-16 h-16 border-2 border-white flex items-center justify-center rotate-45 animate-pulse">
                    <div className="w-4 h-4 bg-white animate-ping" style={{ animationDuration: '1.5s' }} />
                </div>
            </div>

            {/* Brand */}
            <div className="mt-12 text-center">
                <h2 className="text-2xl font-bold tracking-tighter uppercase animate-pulse">Kernal</h2>
                <p className="text-[10px] uppercase tracking-[0.4em] text-zinc-600 mt-2">Loading</p>
            </div>

            {/* Progress Bar */}
            <div className="mt-8 w-48 h-[2px] bg-zinc-900 rounded-full overflow-hidden">
                <div
                    className="h-full bg-white rounded-full page-loading-bar"
                />
            </div>
        </div>
    );
}
