'use client';

import { useState, useEffect } from 'react';
import { Sparkles, Eye, Zap, Monitor, Command, MousePointer, Check } from 'lucide-react';

const demos = [
    { title: 'Voice Command', desc: 'Open Chrome and search for weather', icon: <Command size={20} /> },
    { title: 'Visual Analysis', desc: 'Analyzing screen elements...', icon: <Eye size={20} /> },
    { title: 'Auto Execute', desc: 'Clicking on search bar...', icon: <MousePointer size={20} /> },
];

export function DemoSection() {
    const [activeDemo, setActiveDemo] = useState(0);

    useEffect(() => {
        const timer = setInterval(() => {
            setActiveDemo((prev) => (prev + 1) % demos.length);
        }, 3000);
        return () => clearInterval(timer);
    }, []);

    return (
        <section id="demo" className="py-24 md:py-40 px-6">
            <div className="max-w-6xl mx-auto">
                <div className="grid lg:grid-cols-2 gap-12 items-start">
                    {/* Demo Window */}
                    <div className="demo-window">
                        <div className="demo-titlebar">
                            <div className="demo-dot demo-dot-red"></div>
                            <div className="demo-dot demo-dot-yellow"></div>
                            <div className="demo-dot demo-dot-green"></div>
                            <span className="ml-4 text-xs text-zinc-500 font-mono">kernel-agent.exe</span>
                        </div>
                        <div className="demo-content relative">
                            <div className="space-y-4">
                                <div className="flex items-center gap-3 text-zinc-400">
                                    <Sparkles size={16} className="text-white" />
                                    <span className="text-sm font-mono">Kernal Agent v0.1.2-alpha</span>
                                </div>
                                <div className="h-px bg-zinc-800 my-4"></div>

                                {/* Animated Demo Steps */}
                                {demos.map((demo, i) => (
                                    <div
                                        key={i}
                                        className={`flex items-center gap-3 p-3 rounded-lg transition-all duration-500 ${activeDemo >= i ? 'bg-white/5 border border-white/10' : 'opacity-30'}`}
                                    >
                                        <div className={`${activeDemo >= i ? 'text-white' : 'text-zinc-600'}`}>
                                            {activeDemo > i ? <Check size={20} className="text-white" /> : demo.icon}
                                        </div>
                                        <div>
                                            <div className="text-sm font-medium text-white">{demo.title}</div>
                                            <div className="text-xs text-zinc-500 font-mono">{demo.desc}</div>
                                        </div>
                                        {activeDemo === i && (
                                            <div className="ml-auto">
                                                <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                                            </div>
                                        )}
                                    </div>
                                ))}

                                <div className="mt-6 p-4 bg-white/10 border border-white/20 rounded-lg">
                                    <div className="flex items-center gap-2 text-white">
                                        <Check size={16} />
                                        <span className="text-sm font-medium">Task completed successfully</span>
                                    </div>
                                </div>
                            </div>

                            {/* Animated Cursor */}
                            <div
                                className="absolute w-4 h-4 pointer-events-none transition-all duration-300"
                                style={{
                                    top: `${80 + activeDemo * 60}px`,
                                    left: '40%',
                                }}
                            >
                                <MousePointer size={16} className="text-white drop-shadow-lg" />
                            </div>
                        </div>
                    </div>

                    {/* Demo Description */}
                    <div className="space-y-8">
                        <h3 className="text-3xl md:text-4xl font-bold tracking-tight">Intelligent Desktop Automation</h3>
                        <p className="text-zinc-400 leading-relaxed">
                            Kernal Agent uses Gemini 3&apos;s multimodal capabilities to understand exactly what you want,
                            analyze your screen in real-time, and execute actions with pixel-perfect precision.
                        </p>
                        <div className="space-y-4">
                            {[
                                { icon: <Eye size={20} />, title: 'Visual Understanding', desc: 'Sees and understands any UI, legacy or modern' },
                                { icon: <Zap size={20} />, title: 'Instant Execution', desc: 'Sub-400ms response time for seamless automation' },
                                { icon: <Monitor size={20} />, title: 'System-Wide Access', desc: 'Works across all applications, not just browsers' },
                            ].map((item, i) => (
                                <div key={i} className="flex items-start gap-4 p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/30 transition-colors">
                                    <div className="text-white">{item.icon}</div>
                                    <div>
                                        <div className="font-medium text-white">{item.title}</div>
                                        <div className="text-sm text-zinc-500">{item.desc}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
