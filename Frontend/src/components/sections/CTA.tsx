'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { Download, Users } from 'lucide-react';
import { useScrollProgress } from '@/hooks';

export function CTA() {
    const sectionRef = useRef<HTMLElement>(null);
    const progress = useScrollProgress(sectionRef);
    const [inView, setInView] = useState(false);

    useEffect(() => {
        const observer = new IntersectionObserver(([entry]) => {
            setInView(entry.isIntersecting);
        }, { threshold: 0.2 });
        if (sectionRef.current) observer.observe(sectionRef.current);
        return () => observer.disconnect();
    }, []);

    return (
        <section ref={sectionRef} className="relative py-32 md:py-60 px-6 bg-white text-black text-center overflow-hidden">
            {/* Background Animation */}
            <div className={`absolute inset-0 pointer-events-none transition-all duration-1000 ease-in-out ${inView ? 'opacity-100' : 'opacity-0'}`}>
                <div className={`absolute left-0 top-0 h-full bg-blue-50 transition-all duration-1000 delay-300 ${inView ? 'w-full' : 'w-0'}`}></div>
                <div className={`absolute right-0 top-0 h-full bg-zinc-50 transition-all duration-1000 delay-500 ${inView ? 'w-full' : 'w-0'}`}></div>
            </div>

            {/* Subtle Glow */}
            <div className="absolute inset-0 z-0 pointer-events-none opacity-20">
                <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-400 blur-[120px] rounded-full"></div>
                <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-zinc-400 blur-[100px] rounded-full"></div>
            </div>

            {/* Content */}
            <div
                className="relative z-10 w-full max-w-4xl mx-auto space-y-8 md:space-y-12 transition-all duration-300 ease-out"
                style={{
                    transform: `perspective(1000px) rotateX(${(progress - 0.5) * -15}deg) scale(${0.9 + (1 - Math.abs(progress - 0.5) * 2) * 0.1})`
                }}
            >
                <div className="py-4 md:py-8">
                    <h2 className={`text-5xl sm:text-7xl md:text-8xl font-bold tracking-tighter leading-[1.1] md:leading-tight transition-all duration-1000 ease-out transform ${inView ? 'translate-y-0 opacity-100' : 'translate-y-24 opacity-0'}`}>
                        Ready to <br /><span className="text-zinc-600">delegate?</span>
                    </h2>
                </div>

                <div className={`flex flex-col items-center space-y-6 md:space-y-8 transition-all duration-1000 delay-500 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
                    <Link href="/signup" className="bg-black text-white px-10 md:px-16 py-5 md:py-7 rounded-full font-bold uppercase tracking-widest text-xs md:text-sm hover:scale-110 transition-transform duration-500 shadow-[0_20px_50px_rgba(0,0,0,0.15)] relative overflow-hidden group magnetic-btn">
                        <span className="relative z-10 flex items-center gap-3">
                            <Download size={18} />
                            Get the Agent
                        </span>
                        <div className="absolute inset-0 bg-zinc-800 translate-y-full group-hover:translate-y-0 transition-transform duration-500"></div>
                    </Link>

                    <div className="text-[9px] md:text-xs font-mono uppercase tracking-[0.3em] opacity-40">
                        Windows 11 • Local Execution • v0.1.2-Alpha
                    </div>

                    <div className="flex items-center gap-2 text-sm text-zinc-500">
                        <Users size={16} />
                        <span>Join 2,500+ developers using Kernal Agent</span>
                    </div>
                </div>
            </div>

            {/* Corner Decorations */}
            <div className={`absolute top-0 left-0 w-12 md:w-20 h-12 md:h-20 border-t border-l border-black/10 transition-all duration-1000 delay-700 ${inView ? 'translate-x-4 md:translate-x-10 translate-y-4 md:translate-y-10 opacity-100' : 'translate-x-0 translate-y-0 opacity-0'}`}></div>
            <div className={`absolute bottom-0 right-0 w-12 md:w-20 h-12 md:h-20 border-b border-r border-black/10 transition-all duration-1000 delay-700 ${inView ? '-translate-x-4 md:-translate-x-10 -translate-y-4 md:-translate-y-10 opacity-100' : 'translate-x-0 translate-y-0 opacity-0'}`}></div>
        </section>
    );
}
