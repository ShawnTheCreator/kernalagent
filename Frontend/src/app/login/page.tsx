'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Mail, Lock, Github, AlertCircle } from 'lucide-react';
import { AuthLayout } from '@/components/layout';
import { AuthInput } from '@/components/ui';
import { useAuth } from '@/contexts/AuthContext';

interface FormErrors {
    email?: string;
    password?: string;
    general?: string;
}

export default function LoginPage() {
    const router = useRouter();
    const { login, loginWithGoogle, loginWithGithub, user, loading, error: authError, clearError } = useAuth();

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [errors, setErrors] = useState<FormErrors>({});
    const [touched, setTouched] = useState<{ email?: boolean; password?: boolean }>({});

    // Auto-redirect to dashboard when user is authenticated
    useEffect(() => {
        if (!loading && user) {
            router.push('/dashboard');
        }
    }, [user, loading, router]);

    // Sync auth context error to form errors
    useEffect(() => {
        if (authError) {
            setErrors(prev => ({ ...prev, general: authError }));
        }
    }, [authError]);

    const validateEmail = (email: string): string | undefined => {
        if (!email) return 'Email is required';
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Please enter a valid email';
        return undefined;
    };

    const validatePassword = (password: string): string | undefined => {
        if (!password) return 'Password is required';
        if (password.length < 6) return 'Password must be at least 6 characters';
        return undefined;
    };

    const validateForm = useCallback((): boolean => {
        const newErrors: FormErrors = {
            email: validateEmail(email),
            password: validatePassword(password),
        };
        setErrors(newErrors);
        return !newErrors.email && !newErrors.password;
    }, [email, password]);

    const handleBlur = (field: 'email' | 'password') => {
        setTouched(prev => ({ ...prev, [field]: true }));
        if (field === 'email') {
            setErrors(prev => ({ ...prev, email: validateEmail(email) }));
        } else {
            setErrors(prev => ({ ...prev, password: validatePassword(password) }));
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setTouched({ email: true, password: true });
        clearError();

        if (!validateForm()) return;

        setIsLoading(true);
        setErrors({});

        try {
            await login(email, password);
            // Redirect handled by useEffect above
        } catch (error) {
            setIsLoading(false);
            // Error handled by auth context
        }
    };

    const handleGoogleLogin = async () => {
        clearError();
        setIsLoading(true);
        try {
            await loginWithGoogle();
            // Redirect handled by useEffect above
        } catch (error) {
            setIsLoading(false);
        }
    };

    const handleGithubLogin = async () => {
        clearError();
        setIsLoading(true);
        try {
            await loginWithGithub();
            // Redirect handled by useEffect above
        } catch (error) {
            setIsLoading(false);
        }
    };

    // Show loading while checking auth state
    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-black">
                <div className="w-8 h-8 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
            </div>
        );
    }

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
                            <h1 className="text-3xl font-bold tracking-tight mb-2">Welcome back</h1>
                            <p className="text-zinc-500 text-sm">Sign in to continue to Kernal Agent</p>
                        </div>

                        {/* Social Login - Now functional */}
                        <div className="grid grid-cols-2 gap-3 mb-6">
                            <button
                                onClick={handleGoogleLogin}
                                disabled={isLoading}
                                className="flex items-center justify-center gap-2 bg-white/[0.03] border border-white/10 rounded-xl py-3 px-4 text-sm text-zinc-400 hover:text-white hover:border-white/30 hover:bg-white/[0.05] transition-all duration-300 disabled:opacity-50"
                            >
                                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                                </svg>
                                Google
                            </button>
                            <button
                                onClick={handleGithubLogin}
                                disabled={isLoading}
                                className="flex items-center justify-center gap-2 bg-white/[0.03] border border-white/10 rounded-xl py-3 px-4 text-sm text-zinc-400 hover:text-white hover:border-white/30 hover:bg-white/[0.05] transition-all duration-300 disabled:opacity-50"
                            >
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
                        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
                            {errors.general && (
                                <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm" role="alert">
                                    <AlertCircle size={16} />
                                    <span>{errors.general}</span>
                                </div>
                            )}
                            <AuthInput
                                type="email"
                                placeholder="Email address"
                                icon={<Mail size={18} />}
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                onBlur={() => handleBlur('email')}
                                error={touched.email ? errors.email : undefined}
                                id="login-email"
                            />
                            <AuthInput
                                type="password"
                                placeholder="Password"
                                icon={<Lock size={18} />}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                onBlur={() => handleBlur('password')}
                                error={touched.password ? errors.password : undefined}
                                showPasswordToggle
                                id="login-password"
                            />

                            {/* Forgot Password */}
                            <div className="flex justify-end">
                                <a href="#" className="text-xs text-zinc-500 hover:text-white transition-colors">
                                    Forgot password?
                                </a>
                            </div>

                            {/* Submit Button */}
                            <button
                                type="submit"
                                disabled={isLoading}
                                className="w-full bg-white text-black py-4 rounded-xl font-bold uppercase tracking-widest text-xs hover:bg-zinc-200 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed relative overflow-hidden group"
                            >
                                <span className={`transition-opacity ${isLoading ? 'opacity-0' : 'opacity-100'}`}>
                                    Sign In
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
                            Don&apos;t have an account?{' '}
                            <Link href="/signup" className="text-white hover:underline underline-offset-4">
                                Sign up
                            </Link>
                        </p>
                    </div>
                </div>

                {/* Terms */}
                <p className="text-center text-[10px] text-zinc-600 mt-6 max-w-sm mx-auto">
                    By continuing, you agree to Kernal Agent&apos;s{' '}
                    <a href="#" className="text-zinc-500 hover:text-white transition-colors">Terms of Service</a>
                    {' '}and{' '}
                    <a href="#" className="text-zinc-500 hover:text-white transition-colors">Privacy Policy</a>
                </p>
            </div>
        </AuthLayout>
    );
}
