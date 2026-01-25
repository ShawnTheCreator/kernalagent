'use client';

import { useState } from 'react';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';

interface AuthInputProps {
    type: string;
    placeholder: string;
    icon: React.ReactNode;
    value: string;
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    onBlur?: () => void;
    showPasswordToggle?: boolean;
    error?: string;
    id?: string;
}

export function AuthInput({
    type,
    placeholder,
    icon,
    value,
    onChange,
    onBlur,
    showPasswordToggle,
    error,
    id
}: AuthInputProps) {
    const [showPassword, setShowPassword] = useState(false);
    const inputType = showPasswordToggle ? (showPassword ? 'text' : 'password') : type;
    const inputId = id || `input-${placeholder.toLowerCase().replace(/\s/g, '-')}`;
    const errorId = `${inputId}-error`;

    return (
        <div className="space-y-1">
            <div className="relative group">
                <div className={`absolute left-4 top-1/2 -translate-y-1/2 transition-colors ${error ? 'text-red-400' : 'text-zinc-500 group-focus-within:text-white'}`}>
                    {icon}
                </div>
                <input
                    id={inputId}
                    type={inputType}
                    placeholder={placeholder}
                    value={value}
                    onChange={onChange}
                    onBlur={onBlur}
                    aria-invalid={!!error}
                    aria-describedby={error ? errorId : undefined}
                    className={`w-full bg-white/[0.03] border rounded-xl pl-12 pr-12 py-4 text-white placeholder:text-zinc-600 focus:outline-none focus:bg-white/[0.05] transition-all duration-300 ${error
                            ? 'border-red-400/50 focus:border-red-400'
                            : 'border-white/10 focus:border-white/30'
                        }`}
                />
                {showPasswordToggle && (
                    <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white transition-colors"
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                )}
            </div>
            {error && (
                <div id={errorId} className="flex items-center gap-1.5 text-red-400 text-xs pl-1" role="alert">
                    <AlertCircle size={12} />
                    <span>{error}</span>
                </div>
            )}
        </div>
    );
}

