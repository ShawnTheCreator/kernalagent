'use client';

import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { useMousePosition } from '@/hooks';

interface AuthLayoutProps {
    children: React.ReactNode;
}

export function AuthLayout({ children }: AuthLayoutProps) {
    const { x, y } = useMousePosition();

    return (
        <div className="min-h-screen bg-kernel-bg text-white font-sans overflow-hidden noise-overlay relative flex items-center justify-center px-6 py-12">
            {/* Background Elements */}
            <div
                className="cursor-glow hidden lg:block"
                style={{ left: x, top: y }}
            />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,_#1e1b4b_0%,_transparent_50%)] opacity-20"></div>
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_80%,_#1e1b4b_0%,_transparent_50%)] opacity-10"></div>

            {/* Grid Pattern */}
            <div
                className="absolute inset-0 opacity-[0.03] pointer-events-none"
                style={{
                    backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)',
                    backgroundSize: '60px 60px'
                }}
            />

            {/* Back to Home */}
            <Link
                href="/"
                className="absolute top-8 left-8 flex items-center gap-2 text-zinc-500 hover:text-white transition-colors text-sm group"
            >
                <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                <span>Back to Home</span>
            </Link>

            {/* Logo */}
            <Link href="/" className="absolute top-8 right-8 flex items-center gap-2">
                <div className="w-5 h-5 border border-white flex items-center justify-center rotate-45">
                    <div className="w-1.5 h-1.5 bg-white"></div>
                </div>
                <span className="font-bold tracking-tighter text-lg uppercase">Kernal</span>
            </Link>

            {children}
        </div>
    );
}
