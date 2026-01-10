'use client';

import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

interface AuthInputProps {
    type: string;
    placeholder: string;
    icon: React.ReactNode;
    value: string;
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    showPasswordToggle?: boolean;
}

export function AuthInput({ type, placeholder, icon, value, onChange, showPasswordToggle }: AuthInputProps) {
    const [showPassword, setShowPassword] = useState(false);
    const inputType = showPasswordToggle ? (showPassword ? 'text' : 'password') : type;

    return (
        <div className="relative group">
            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-white transition-colors">
                {icon}
            </div>
            <input
                type={inputType}
                placeholder={placeholder}
                value={value}
                onChange={onChange}
                className="w-full bg-white/[0.03] border border-white/10 rounded-xl pl-12 pr-12 py-4 text-white placeholder:text-zinc-600 focus:outline-none focus:border-white/30 focus:bg-white/[0.05] transition-all duration-300"
            />
            {showPasswordToggle && (
                <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white transition-colors"
                >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
            )}
        </div>
    );
}
