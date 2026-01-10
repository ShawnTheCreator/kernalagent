'use client';

import { useEffect, useRef } from 'react';
import Lenis from 'lenis';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export function SmoothScrollProvider({ children }: { children: React.ReactNode }) {
    const lenisRef = useRef<Lenis | null>(null);

    useEffect(() => {
        // Initialize Lenis smooth scroll
        lenisRef.current = new Lenis({
            duration: 1.2,
            easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
            orientation: 'vertical',
            smoothWheel: true,
        });

        // Connect Lenis to GSAP ScrollTrigger
        lenisRef.current.on('scroll', ScrollTrigger.update);

        gsap.ticker.add((time) => {
            lenisRef.current?.raf(time * 1000);
        });

        gsap.ticker.lagSmoothing(0);

        return () => {
            lenisRef.current?.destroy();
            gsap.ticker.remove((time) => {
                lenisRef.current?.raf(time * 1000);
            });
        };
    }, []);

    return <>{children}</>;
}

// Hook to use Lenis instance
export function useSmoothScroll() {
    return {
        scrollTo: (target: string | number | HTMLElement) => {
            const lenis = document.querySelector('[data-lenis]') as HTMLElement & { lenis?: Lenis };
            lenis?.lenis?.scrollTo(target);
        }
    };
}
