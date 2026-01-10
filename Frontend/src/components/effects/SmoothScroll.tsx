'use client';

import { useEffect, useRef, useState } from 'react';

export function SmoothScrollProvider({ children }: { children: React.ReactNode }) {
    const lenisRef = useRef<unknown>(null);
    const [isMounted, setIsMounted] = useState(false);

    useEffect(() => {
        setIsMounted(true);

        // Dynamic import to avoid SSR issues
        import('lenis').then(({ default: Lenis }) => {
            lenisRef.current = new Lenis({
                duration: 1.2,
                easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)), // Exponential ease out
                orientation: 'vertical',
                gestureOrientation: 'vertical',
                smoothWheel: true,
                touchMultiplier: 2,
            });

            // RAF loop
            function raf(time: number) {
                (lenisRef.current as { raf: (time: number) => void })?.raf(time);
                requestAnimationFrame(raf);
            }
            requestAnimationFrame(raf);
        });

        // Cleanup
        return () => {
            if (lenisRef.current) {
                (lenisRef.current as { destroy: () => void }).destroy();
            }
        };
    }, []);

    // Don't render children until mounted to avoid hydration issues
    if (!isMounted) {
        return <>{children}</>;
    }

    return <>{children}</>;
}

// Hook to access Lenis instance
export function useSmoothScroll() {
    const scrollTo = (target: string | number) => {
        const element = typeof target === 'string' ? document.querySelector(target) : null;
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else if (typeof target === 'number') {
            window.scrollTo({ top: target, behavior: 'smooth' });
        }
    };

    return { scrollTo };
}
