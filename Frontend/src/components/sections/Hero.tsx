'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { Download, Play, ArrowRight, CircleDot, Terminal } from 'lucide-react';
import { useMousePosition, useScrollProgress } from '@/hooks';

export function Hero() {
    const [scrollY, setScrollY] = useState(0);
    const containerRef = useRef<HTMLElement>(null);
    const progress = useScrollProgress(containerRef);
    const [typedText, setTypedText] = useState('');
    const fullText = 'Synthesized.';
    const { x, y } = useMousePosition();
    const [windowSize, setWindowSize] = useState({ width: 0, height: 0 });

    useEffect(() => {
        setWindowSize({ width: window.innerWidth, height: window.innerHeight });
        const handleResize = () => setWindowSize({ width: window.innerWidth, height: window.innerHeight });
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    useEffect(() => {
        const handleScroll = () => setScrollY(window.pageYOffset);
        window.addEventListener('scroll', handleScroll, { passive: true });
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    useEffect(() => {
        let i = 0;
        const timer = setInterval(() => {
            if (i <= fullText.length) {
                setTypedText(fullText.slice(0, i));
                i++;
            } else {
                clearInterval(timer);
            }
        }, 100);
        return () => clearInterval(timer);
    }, []);

    return (
        <section ref={containerRef} className="relative min-h-screen flex flex-col items-center justify-center px-6 overflow-hidden pt-20">
            {/* Floating Elements */}
            <div
                className="absolute top-20 left-[10%] opacity-20 animate-float hidden lg:block"
                style={{ transform: `translate(${(x - windowSize.width / 2) * 0.02}px, ${(y - windowSize.height / 2) * 0.02}px)` }}
            >
                <div className="w-24 h-24 border border-white/30 rounded-xl rotate-12"></div>
            </div>
            <div
                className="absolute bottom-40 right-[15%] opacity-20 animate-float-delayed hidden lg:block"
                style={{ transform: `translate(${(x - windowSize.width / 2) * -0.015}px, ${(y - windowSize.height / 2) * -0.015}px)` }}
            >
                <div className="w-16 h-16 border border-white/30 rounded-full"></div>
            </div>
            <div
                className="absolute top-1/3 right-[8%] opacity-10 hidden lg:block"
                style={{ transform: `translate(${(x - windowSize.width / 2) * 0.03}px, ${(y - windowSize.height / 2) * 0.03}px)` }}
            >
                <Terminal size={80} className="text-white" />
            </div>

            {/* Background Effects */}
            <div
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[160vw] h-[160vh] opacity-10 pointer-events-none transition-transform duration-150 ease-out"
                style={{ transform: `translate(-50%, -50%) translateY(${scrollY * 0.3}px) rotate(${scrollY * 0.02}deg)` }}
            >
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_#1e1b4b_0%,_transparent_70%)] blur-[160px]"></div>
            </div>

            <div
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[140vw] h-[140vh] opacity-20 pointer-events-none transition-transform duration-100 ease-out"
                style={{ transform: `translate(-50%, -50%) translateY(${scrollY * 0.15}px) scale(${1 + scrollY * 0.0001})` }}
            >
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_#3b82f6_0%,_transparent_60%)] blur-[120px] animate-pulse"></div>
            </div>

            {/* Content */}
            <div
                className="relative z-10 w-full max-w-6xl text-center space-y-6 md:space-y-8 transition-all duration-300 ease-out"
                style={{
                    transform: `perspective(1000px) rotateX(${progress * 15}deg) scale(${1 - progress * 0.2})`,
                    opacity: 1 - progress * 0.5
                }}
            >
                {/* Badge */}
                <div className="inline-flex items-center space-x-2 px-4 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm mb-2 animate-fade-in">
                    <CircleDot size={10} className="text-white animate-pulse" />
                    <span className="text-[8px] md:text-[10px] font-mono tracking-widest uppercase text-zinc-400">Gemini 3 Cognitive Layer Activated</span>
                    <span className="text-[8px] md:text-[10px] font-mono tracking-widest uppercase text-white">• LIVE</span>
                </div>

                {/* Main Title */}
                <h1 className="text-5xl sm:text-7xl md:text-[100px] lg:text-[120px] font-bold tracking-[-0.06em] leading-[0.9] mb-4 md:mb-8">
                    The Desktop,<br />
                    <span className="text-zinc-400">{typedText}</span>
                    <span className="inline-block w-[3px] h-[0.9em] bg-white ml-1 animate-blink align-baseline"></span>
                </h1>

                {/* Subtitle */}
                <p className="text-lg md:text-2xl text-zinc-400 max-w-2xl mx-auto font-light tracking-tight leading-relaxed">
                    A native cognitive agent that <span className="text-white font-medium">sees</span>, <span className="text-white font-medium">understands</span>, and <span className="text-white font-medium">executes</span> across your operating system.
                </p>

                {/* CTAs */}
                <div className="flex flex-col sm:flex-row items-center justify-center space-y-6 sm:space-y-0 sm:space-x-8 pt-8 md:pt-10">
                    <Link href="/signup" className="group flex items-center space-x-3 bg-white text-black px-8 py-4 rounded-full font-bold uppercase tracking-widest text-xs hover:scale-105 transition-all duration-500">
                        <Download size={18} />
                        <span>Install for Windows</span>
                    </Link>

                    <a href="#demo" className="group flex items-center space-x-2 text-[10px] uppercase tracking-[0.2em] text-zinc-400 hover:text-white transition-colors">
                        <Play size={14} className="group-hover:scale-110 transition-transform" />
                        <span>Watch Demo</span>
                        <ArrowRight size={12} className="group-hover:translate-x-1 transition-transform" />
                    </a>
                </div>

                {/* Stats Row */}
                <div className="flex justify-center gap-12 pt-12">
                    <div className="text-center">
                        <div className="text-2xl md:text-3xl font-bold text-white">2.5K+</div>
                        <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-1">Active Users</div>
                    </div>
                    <div className="text-center">
                        <div className="text-2xl md:text-3xl font-bold text-white">&lt;400ms</div>
                        <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-1">Response Time</div>
                    </div>
                    <div className="text-center">
                        <div className="text-2xl md:text-3xl font-bold text-white">100%</div>
                        <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-1">Local Execution</div>
                    </div>
                </div>
            </div>
        </section>
    );
}
