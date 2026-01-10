'use client';

import { useState, useEffect, useRef } from 'react';
import { Star } from 'lucide-react';

// Custom hook for counting up
function useCountUp(target: number, duration: number, start: boolean) {
    const [count, setCount] = useState(0);

    useEffect(() => {
        if (!start) return;

        let startTime: number | null = null;
        const step = (timestamp: number) => {
            if (!startTime) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);
            setCount(Math.floor(progress * target));
            if (progress < 1) {
                requestAnimationFrame(step);
            }
        };
        requestAnimationFrame(step);
    }, [target, duration, start]);

    return count;
}

export function StatsSection() {
    const ref = useRef<HTMLElement>(null);
    const [inView, setInView] = useState(false);
    const users = useCountUp(2547, 2000, inView);
    const tasks = useCountUp(150000, 2500, inView);
    const uptime = useCountUp(99, 1500, inView);

    useEffect(() => {
        const observer = new IntersectionObserver(([entry]) => {
            if (entry.isIntersecting) setInView(true);
        }, { threshold: 0.2 });
        if (ref.current) observer.observe(ref.current);
        return () => observer.disconnect();
    }, []);

    return (
        <section ref={ref} className="py-24 px-6 border-y border-zinc-900 bg-gradient-to-b from-transparent via-blue-950/5 to-transparent">
            <div className="max-w-5xl mx-auto grid md:grid-cols-4 gap-8 text-center">
                <div>
                    <div className="text-4xl md:text-5xl font-bold text-white">{users.toLocaleString()}+</div>
                    <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-2">Active Users</div>
                </div>
                <div>
                    <div className="text-4xl md:text-5xl font-bold text-white">{tasks.toLocaleString()}+</div>
                    <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-2">Tasks Executed</div>
                </div>
                <div>
                    <div className="text-4xl md:text-5xl font-bold text-white">{uptime}.9%</div>
                    <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-2">Uptime</div>
                </div>
                <div>
                    <div className="flex items-center justify-center text-4xl md:text-5xl font-bold text-white">
                        4.9 <Star size={28} className="ml-2" fill="currentColor" />
                    </div>
                    <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-2">User Rating</div>
                </div>
            </div>
        </section>
    );
}
