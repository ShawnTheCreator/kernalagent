'use client';

import { useRef, useState, useEffect } from 'react';
import { Eye, Zap, Layers, Sparkles, Command, Terminal, Shield, Cpu } from 'lucide-react';

export function BentoFeatures() {
    const ref = useRef<HTMLElement>(null);
    const [inView, setInView] = useState(false);

    useEffect(() => {
        const observer = new IntersectionObserver(([entry]) => {
            if (entry.isIntersecting) setInView(true);
        }, { threshold: 0.1 });
        if (ref.current) observer.observe(ref.current);
        return () => observer.disconnect();
    }, []);

    return (
        <section id="features" className="py-24 md:py-40 px-6" ref={ref}>
            <div className="max-w-6xl mx-auto">
                <div className={`bento-grid ${inView ? 'stagger-in' : ''}`}>
                    {/* Large Feature - Multimodal Vision */}
                    <div className="bento-item bento-large flex flex-col justify-between">
                        <div>
                            <div className="text-white mb-4"><Eye size={32} /></div>
                            <h3 className="text-2xl font-bold mb-2">Multimodal Vision</h3>
                            <p className="text-zinc-500 text-sm">Real-time visual parsing using Gemini 3 Vision. Kernal Agent sees your screen exactly as you do.</p>
                        </div>
                        <div className="mt-6 p-4 bg-white/[0.02] rounded-xl border border-white/5">
                            <div className="grid grid-cols-3 gap-2">
                                {[1, 2, 3, 4, 5, 6].map(i => (
                                    <div key={i} className="aspect-video bg-white/5 rounded animate-pulse" style={{ animationDelay: `${i * 100}ms` }}></div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Sub-400ms Latency - NOW TO THE RIGHT (spans 1 col, 2 rows) */}
                    <div className="bento-item row-span-2 flex flex-col justify-between">
                        <div>
                            <div className="text-white mb-4"><Zap size={32} /></div>
                            <h3 className="text-2xl font-bold mb-2">Sub-400ms Latency</h3>
                            <p className="text-zinc-500 text-sm">Optimized inference pipeline for near-instant response. Feel the speed.</p>
                        </div>
                        <div className="mt-6 space-y-3">
                            <div className="flex items-center gap-2">
                                <div className="h-2 flex-1 bg-zinc-900 rounded-full overflow-hidden">
                                    <div className="h-full w-[85%] bg-white rounded-full animate-pulse"></div>
                                </div>
                                <span className="text-xs text-zinc-600">~380ms</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="h-2 flex-1 bg-zinc-900 rounded-full overflow-hidden">
                                    <div className="h-full w-[60%] bg-white/60 rounded-full animate-pulse" style={{ animationDelay: '200ms' }}></div>
                                </div>
                                <span className="text-xs text-zinc-600">Vision</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="h-2 flex-1 bg-zinc-900 rounded-full overflow-hidden">
                                    <div className="h-full w-[40%] bg-white/40 rounded-full animate-pulse" style={{ animationDelay: '400ms' }}></div>
                                </div>
                                <span className="text-xs text-zinc-600">Execute</span>
                            </div>
                        </div>
                        <div className="mt-6 p-4 bg-white/[0.02] rounded-xl border border-white/5 text-center">
                            <div className="text-3xl font-mono font-bold text-white">&lt;400</div>
                            <div className="text-[10px] uppercase tracking-widest text-zinc-600 mt-1">milliseconds</div>
                        </div>
                    </div>

                    {/* Small Features Row */}
                    <div className="bento-item">
                        <div className="text-white mb-3"><Layers size={24} /></div>
                        <h3 className="font-bold mb-1">Multi-step Reasoning</h3>
                        <p className="text-zinc-500 text-xs">Complex chains of thought with state management.</p>
                    </div>

                    <div className="bento-item">
                        <div className="text-white mb-3"><Command size={24} /></div>
                        <h3 className="font-bold mb-1">System Control</h3>
                        <p className="text-zinc-500 text-xs">Full OS-level access. Files, apps, settings.</p>
                    </div>

                    <div className="bento-item">
                        <div className="text-white mb-3"><Terminal size={24} /></div>
                        <h3 className="font-bold mb-1">CLI Integration</h3>
                        <p className="text-zinc-500 text-xs">Execute terminal commands seamlessly.</p>
                    </div>

                    {/* Wide Feature - Natural Language */}
                    <div className="bento-item bento-wide">
                        <div className="flex items-start gap-4">
                            <div className="text-white"><Sparkles size={28} /></div>
                            <div className="flex-1">
                                <h3 className="text-xl font-bold mb-2">Natural Language</h3>
                                <p className="text-zinc-500 text-sm">Just describe what you want. Kernal Agent figures out the rest.</p>
                                <div className="mt-3 p-3 bg-zinc-900 rounded-lg font-mono text-xs text-zinc-400">
                                    <span className="text-white">&quot;</span>Open Spotify and play my discover weekly<span className="text-white">&quot;</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Extra Feature - Security */}
                    <div className="bento-item">
                        <div className="text-white mb-3"><Shield size={24} /></div>
                        <h3 className="font-bold mb-1">Local First Security</h3>
                        <p className="text-zinc-500 text-xs">All processing happens on your machine. Your data stays private.</p>
                    </div>
                </div>
            </div>
        </section>
    );
}
