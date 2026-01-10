'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Mail, Lock, User, Github, Check } from 'lucide-react';
import { AuthLayout } from '@/components/layout';
import { AuthInput } from '@/components/ui';

export default function SignupPage() {
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setTimeout(() => setIsLoading(false), 1500);
    };

    // Password strength indicators
    const hasMinLength = password.length >= 8;
    const hasUppercase = /[A-Z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    const hasSpecial = /[!@#$%^&*]/.test(password);

    return (
        <AuthLayout>
            <div className="w-full max-w-md">
                {/* Auth Card */}
                <div className="relative">
                    {/* Glow effect */}
                    <div className="absolute -inset-1 bg-gradient-to-r from-white/10 via-white/5 to-white/10 rounded-2xl blur-xl opacity-50"></div>

                    <div className="relative bg-zinc-950/80 backdrop-blur-xl border border-white/10 rounded-2xl p-8 md:p-10">
                        {/* Header */}
                        <div className="text-center mb-8">
                            <h1 className="text-3xl font-bold tracking-tight mb-2">Create account</h1>
                            <p className="text-zinc-500 text-sm">Start automating with Kernal Agent today</p>
                        </div>

                        {/* Social Login */}
                        <div className="grid grid-cols-2 gap-3 mb-6">
                            <button className="flex items-center justify-center gap-2 bg-white/[0.03] border border-white/10 rounded-xl py-3 px-4 text-sm text-zinc-400 hover:text-white hover:border-white/30 hover:bg-white/[0.05] transition-all duration-300">
                                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                                </svg>
                                Google
                            </button>
                            <button className="flex items-center justify-center gap-2 bg-white/[0.03] border border-white/10 rounded-xl py-3 px-4 text-sm text-zinc-400 hover:text-white hover:border-white/30 hover:bg-white/[0.05] transition-all duration-300">
                                <Github size={18} />
                                GitHub
                            </button>
                        </div>

                        {/* Divider */}
                        <div className="relative my-6">
                            <div className="absolute inset-0 flex items-center">
                                <div className="w-full border-t border-white/10"></div>
                            </div>
                            <div className="relative flex justify-center text-xs">
                                <span className="bg-zinc-950 px-4 text-zinc-600 uppercase tracking-widest">or continue with</span>
                            </div>
                        </div>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <AuthInput
                                type="text"
                                placeholder="Full name"
                                icon={<User size={18} />}
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                            />
                            <AuthInput
                                type="email"
                                placeholder="Email address"
                                icon={<Mail size={18} />}
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                            />
                            <AuthInput
                                type="password"
                                placeholder="Password"
                                icon={<Lock size={18} />}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                showPasswordToggle
                            />

                            {/* Password Strength */}
                            {password.length > 0 && (
                                <div className="space-y-2 p-3 bg-white/[0.02] rounded-lg border border-white/5">
                                    <div className="text-[10px] uppercase tracking-widest text-zinc-600 mb-2">Password strength</div>
                                    <div className="grid grid-cols-2 gap-2 text-xs">
                                        <div className={`flex items-center gap-2 ${hasMinLength ? 'text-white' : 'text-zinc-600'}`}>
                                            <Check size={12} /> 8+ characters
                                        </div>
                                        <div className={`flex items-center gap-2 ${hasUppercase ? 'text-white' : 'text-zinc-600'}`}>
                                            <Check size={12} /> Uppercase
                                        </div>
                                        <div className={`flex items-center gap-2 ${hasNumber ? 'text-white' : 'text-zinc-600'}`}>
                                            <Check size={12} /> Number
                                        </div>
                                        <div className={`flex items-center gap-2 ${hasSpecial ? 'text-white' : 'text-zinc-600'}`}>
                                            <Check size={12} /> Special char
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Submit Button */}
                            <button
                                type="submit"
                                disabled={isLoading}
                                className="w-full bg-white text-black py-4 rounded-xl font-bold uppercase tracking-widest text-xs hover:bg-zinc-200 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed relative overflow-hidden group"
                            >
                                <span className={`transition-opacity ${isLoading ? 'opacity-0' : 'opacity-100'}`}>
                                    Create Account
                                </span>
                                {isLoading && (
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <div className="w-5 h-5 border-2 border-black/20 border-t-black rounded-full animate-spin"></div>
                                    </div>
                                )}
                            </button>
                        </form>

                        {/* Footer */}
                        <p className="text-center text-sm text-zinc-500 mt-6">
                            Already have an account?{' '}
                            <Link href="/login" className="text-white hover:underline underline-offset-4">
                                Sign in
                            </Link>
                        </p>
                    </div>
                </div>

                {/* Terms */}
                <p className="text-center text-[10px] text-zinc-600 mt-6 max-w-sm mx-auto">
                    By creating an account, you agree to Kernal Agent&apos;s{' '}
                    <a href="#" className="text-zinc-500 hover:text-white transition-colors">Terms of Service</a>
                    {' '}and{' '}
                    <a href="#" className="text-zinc-500 hover:text-white transition-colors">Privacy Policy</a>
                </p>
            </div>
        </AuthLayout>
    );
}
