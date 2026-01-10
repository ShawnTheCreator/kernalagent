'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Menu, X } from 'lucide-react';

export function Navbar() {
    const [scrolled, setScrolled] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 50);
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <>
            <nav className={`fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 md:px-10 py-4 md:py-6 transition-all duration-500 ${scrolled ? 'bg-kernel-bg/80 backdrop-blur-xl border-b border-white/5' : ''}`}>
                <div className="flex items-center space-x-2 md:space-x-3 w-1/4">
                    <div className="w-5 h-5 md:w-6 md:h-6 border border-white flex items-center justify-center rotate-45">
                        <div className="w-1.5 h-1.5 md:w-2 md:h-2 bg-white"></div>
                    </div>
                    <Link href="/" className="font-bold tracking-tighter text-lg md:text-xl uppercase text-white">
                        Kernal
                    </Link>
                </div>

                <div className="hidden lg:flex flex-1 justify-center items-center space-x-12 text-[10px] uppercase tracking-[0.3em] font-medium text-white/60">
                    <a href="#features" className="hover:text-white transition-colors">Features</a>
                    <a href="#demo" className="hover:text-white transition-colors">Demo</a>
                    <a href="#tech" className="hover:text-white transition-colors">Architecture</a>
                </div>

                <div className="flex justify-end w-1/4 items-center gap-4">
                    <Link href="/login" className="hidden md:block text-[10px] uppercase tracking-widest text-zinc-400 hover:text-white transition-colors">
                        Sign In
                    </Link>
                    <Link href="/signup" className="hidden md:block text-[9px] md:text-[10px] uppercase tracking-widest border border-white/20 px-4 md:px-6 py-2 rounded-full hover:bg-white hover:text-black transition-all duration-500 text-white whitespace-nowrap magnetic-btn">
                        Get Started
                    </Link>
                    <button
                        className="lg:hidden text-white p-2"
                        onClick={() => setMobileMenuOpen(true)}
                    >
                        <Menu size={24} />
                    </button>
                </div>
            </nav>

            {/* Mobile Menu */}
            <div className={`mobile-menu-overlay ${mobileMenuOpen ? 'open' : ''}`} onClick={() => setMobileMenuOpen(false)} />
            <div className={`mobile-menu ${mobileMenuOpen ? 'open' : ''}`}>
                <button
                    className="absolute top-6 right-6 text-white"
                    onClick={() => setMobileMenuOpen(false)}
                >
                    <X size={24} />
                </button>
                <div className="flex flex-col space-y-8 text-xl uppercase tracking-widest">
                    <a href="#features" className="text-white/60 hover:text-white transition-colors" onClick={() => setMobileMenuOpen(false)}>Features</a>
                    <a href="#demo" className="text-white/60 hover:text-white transition-colors" onClick={() => setMobileMenuOpen(false)}>Demo</a>
                    <a href="#tech" className="text-white/60 hover:text-white transition-colors" onClick={() => setMobileMenuOpen(false)}>Architecture</a>
                    <div className="pt-8 border-t border-white/10 space-y-4">
                        <Link href="/login" className="block text-sm text-white/60 hover:text-white transition-colors" onClick={() => setMobileMenuOpen(false)}>Sign In</Link>
                        <Link href="/signup" className="block text-sm uppercase tracking-widest border border-white/20 px-6 py-3 rounded-full hover:bg-white hover:text-black transition-all duration-500 text-white text-center" onClick={() => setMobileMenuOpen(false)}>
                            Get Started
                        </Link>
                    </div>
                </div>
            </div>
        </>
    );
}
