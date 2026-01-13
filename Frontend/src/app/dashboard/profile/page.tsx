'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
    User,
    Mail,
    Calendar,
    Shield,
    Camera,
    Github,
    // Chrome, // Chrome icon not available in lucide-react, using Globe or similar
    Globe,
    Save,
    MapPin,
    Link as LinkIcon,
    Loader2
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { AuthInput } from '@/components/ui';

import { useRef } from 'react';
import { supabase } from '@/lib/supabase';

export default function ProfilePage() {
    const { user, updateUser, loading: authLoading } = useAuth();
    const router = useRouter();
    const [isEditing, setIsEditing] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Form State
    const [displayName, setDisplayName] = useState('');
    const [bio, setBio] = useState('');
    const [location, setLocation] = useState('');
    const [website, setWebsite] = useState('');
    const [photoURL, setPhotoURL] = useState('');

    const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

    // Redirect to login if not authenticated
    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [authLoading, user, router]);

    // Fetch Profile Data
    useEffect(() => {
        const fetchProfile = async () => {
            if (!user) return;
            try {
                const token = await user.getIdToken();
                const response = await fetch(`${API_BASE}/me`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    setDisplayName(data.name || user.displayName || '');
                    setBio(data.bio || '');
                    setLocation(data.location || '');
                    setWebsite(data.website || '');
                    setPhotoURL(data.photoURL || user.photoURL || '');
                }
            } catch (error) {
                console.error('Failed to fetch profile:', error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchProfile();
    }, [user]);

    // Handle Image Upload
    const handleImageUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file || !user) return;

        setIsUploading(true);
        try {
            const fileExt = file.name.split('.').pop();
            const fileName = `${user.uid}-${Date.now()}.${fileExt}`;
            const filePath = `${fileName}`;

            // Upload to Supabase
            const { error: uploadError } = await supabase.storage
                .from('avatars')
                .upload(filePath, file);

            if (uploadError) {
                throw uploadError;
            }

            // Get Public URL
            const { data: { publicUrl } } = supabase.storage
                .from('avatars')
                .getPublicUrl(filePath);

            setPhotoURL(publicUrl);
            console.log('Image uploaded successfully:', publicUrl);

            // Update Auth Context Immediately for UI Sync
            await updateUser({ photoURL: publicUrl });

            // Auto-save the new photo URL to backend
            await saveProfileData(publicUrl);

        } catch (error) {
            console.error('Error uploading image:', error);
            // Revert to old photo if upload fails
            setPhotoURL(user.photoURL || '');
        } finally {
            setIsUploading(false);
        }
    };

    // Helper to save profile data
    const saveProfileData = async (newPhotoUrl?: string) => {
        try {
            const token = await user?.getIdToken();
            const response = await fetch(`${API_BASE}/me`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: displayName,
                    bio,
                    location,
                    website,
                    photoURL: newPhotoUrl || photoURL
                })
            });

            if (!response.ok) {
                throw new Error('Failed to update backend');
            }
            console.log('Profile saved successfully');
        } catch (error) {
            console.error('Error saving profile:', error);
        }
    };

    // Save Profile Data (Manual Save)
    const handleSave = async () => {
        setIsSaving(true);

        // Update auth context first for immediate UI feedback
        if (displayName !== user?.displayName) {
            await updateUser({ displayName });
        }

        await saveProfileData();
        setIsEditing(false);
        setIsSaving(false);
    };

    // Stats (Mock data for now, could be fetched from API later)
    const stats = [
        { label: 'Role', value: 'Administrator', icon: <Shield size={16} className="text-purple-400" /> },
        { label: 'Plan', value: 'Pro / Unlimited', icon: <SparklesIcon className="w-4 h-4 text-amber-400" /> },
        { label: 'Joined', value: 'Jan 2024', icon: <Calendar size={16} className="text-blue-400" /> },
    ];

    // Show loading state or redirect if not authenticated
    if (authLoading || !user) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Loader2 className="w-8 h-8 animate-spin text-zinc-500" />
            </div>
        );
    }

    return (
        <div className="space-y-8 pb-10">
            {/* Hidden File Input */}
            <input
                type="file"
                ref={fileInputRef}
                onChange={handleImageUpload}
                accept="image/*"
                className="hidden"
            />

            {/* Header / Hero */}
            <div className="relative h-64 w-full rounded-2xl overflow-hidden group">
                {/* Abstract Gradient Cover */}
                <div className="absolute inset-0 bg-gradient-to-r from-indigo-900 via-purple-900 to-zinc-900 animate-gradient-xy"></div>
                <div className="absolute inset-0 bg-[url('/grid-pattern.svg')] opacity-20"></div>

                {/* Overlay Text */}
                <div className="absolute bottom-6 left-8 z-10 hidden md:block">
                    <h1 className="text-3xl font-black text-white tracking-tight">PROFILE</h1>
                    <p className="text-white/60 text-sm">Manage your public identity</p>
                </div>

                {/* Edit Cover Button */}
                <button className="absolute top-4 right-4 bg-black/40 backdrop-blur-md border border-white/10 text-white/80 p-2 rounded-lg hover:bg-white/10 transition-colors opacity-0 group-hover:opacity-100">
                    <Camera size={18} />
                </button>
            </div>

            <div className="px-4 md:px-8 -mt-20 relative z-20 flex flex-col md:flex-row gap-8 items-start">

                {/* Left Column: Avatar & Quick Info */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="w-full md:w-80 flex-shrink-0 space-y-6"
                >
                    {/* Avatar Card */}
                    <div className="bg-[#0A0A0A] border border-zinc-800 rounded-2xl p-6 flex flex-col items-center text-center shadow-2xl relative overflow-hidden">
                        {/* Shine Effect */}
                        <div className="absolute inset-0 bg-gradient-to-tr from-white/5 to-transparent pointer-events-none"></div>

                        <div
                            className="relative w-32 h-32 mb-4 group cursor-pointer"
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <div className="w-full h-full rounded-full border-4 border-[#0A0A0A] overflow-hidden shadow-lg relative z-10 bg-zinc-800">
                                {isUploading ? (
                                    <div className="w-full h-full flex items-center justify-center bg-black/50">
                                        <Loader2 className="w-8 h-8 text-white animate-spin" />
                                    </div>
                                ) : photoURL ? (
                                    <img src={photoURL} alt="Profile" className="w-full h-full object-cover" />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center text-3xl font-bold text-zinc-500">
                                        {displayName?.[0] || 'U'}
                                    </div>
                                )}
                            </div>

                            {/* Edit Avatar Overlay (Desktop) */}
                            <div className="absolute inset-0 rounded-full bg-black/60 flex items-center justify-center opacity-0 lg:group-hover:opacity-100 transition-opacity z-20 border-4 border-transparent pointer-events-none">
                                <Camera size={24} className="text-white" />
                            </div>
                        </div>

                        {/* Mobile Edit Badge (Always visible, outside the overflow-hidden container) */}
                        <div className="absolute bottom-6 right-6 bg-zinc-800 p-2 rounded-full border border-zinc-700 shadow-lg lg:hidden z-30 pointer-events-none">
                            <Camera size={16} className="text-white" />
                        </div>
                    </div>

                    <h2 className="text-xl font-bold text-white mb-1">{displayName || 'Ghost User'}</h2>
                    <p className="text-zinc-500 text-sm mb-6">{user?.email}</p>

                    <div className="w-full grid grid-cols-2 gap-2 mb-6">
                        <div className="bg-zinc-900/50 p-3 rounded-xl border border-zinc-800/50">
                            <div className="text-xl font-bold text-white">124</div>
                            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Actions</div>
                        </div>
                        <div className="bg-zinc-900/50 p-3 rounded-xl border border-zinc-800/50">
                            <div className="text-xl font-bold text-white">89%</div>
                            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Success</div>
                        </div>
                    </div>

                    <button className="w-full py-2.5 bg-white text-black font-bold rounded-xl hover:bg-zinc-200 transition-colors text-sm">
                        Upgrade Plan
                    </button>

                    {/* Social Links */}
                    <div className="bg-[#0A0A0A] border border-zinc-800 rounded-2xl p-6 space-y-4">
                        <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Connected Accounts</h3>

                        <div className="flex items-center justify-between p-3 bg-zinc-900/50 rounded-xl border border-zinc-800/50">
                            <div className="flex items-center gap-3">
                                <div className="bg-white/10 p-2 rounded-lg">
                                    <Globe size={18} className="text-blue-400" />
                                </div>
                                <div>
                                    <div className="text-sm font-medium text-zinc-200">Google</div>
                                    <div className="text-xs text-zinc-500">Connected</div>
                                </div>
                            </div>
                            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        </div>

                        <div className="flex items-center justify-between p-3 bg-zinc-900/50 rounded-xl border border-zinc-800/50">
                            <div className="flex items-center gap-3">
                                <div className="bg-white/10 p-2 rounded-lg">
                                    <Github size={18} className="text-white" />
                                </div>
                                <div>
                                    <div className="text-sm font-medium text-zinc-200">GitHub</div>
                                    <div className="text-xs text-zinc-500">Not Connected</div>
                                </div>
                            </div>
                            <div className="w-2 h-2 bg-zinc-700 rounded-full"></div>
                        </div>
                    </div>
                </motion.div>

                {/* Right Column: Edit Profile Form */}
                <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 }}
                    className="flex-1 bg-[#0A0A0A] border border-zinc-800 rounded-2xl p-8 w-full"
                >
                    <div className="flex items-center justify-between mb-8">
                        <div>
                            <h2 className="text-xl font-bold text-white">Profile Information</h2>
                            <p className="text-zinc-500 text-sm">Update your account's profile information and email address.</p>
                        </div>
                        <button
                            onClick={isEditing ? handleSave : () => setIsEditing(true)}
                            className={`
                                flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                                ${isEditing
                                    ? 'bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-500/20'
                                    : 'bg-zinc-800 text-zinc-300 hover:text-white hover:bg-zinc-700'
                                }
                            `}
                        >
                            {isEditing ? (
                                <>
                                    <Save size={16} /> Save Changes
                                </>
                            ) : (
                                'Edit Profile'
                            )}
                        </button>
                    </div>

                    <div className="space-y-6">
                        {/* Name & Email Row */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-zinc-500 uppercase">Display Name</label>
                                <div className="relative">
                                    <User size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                                    <input
                                        type="text"
                                        value={displayName}
                                        onChange={(e) => setDisplayName(e.target.value)}
                                        disabled={!isEditing}
                                        className={`
                                            w-full bg-zinc-900/50 border border-zinc-800 rounded-xl py-3 pl-10 pr-4 text-sm text-zinc-200 focus:outline-none transition-all
                                            ${isEditing ? 'focus:border-blue-500 focus:ring-1 focus:ring-blue-500 cursor-text' : 'opacity-60 cursor-not-allowed'}
                                        `}
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-zinc-500 uppercase">Email Address</label>
                                <div className="relative">
                                    <Mail size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                                    <input
                                        type="email"
                                        value={user?.email || ''}
                                        disabled
                                        className="w-full bg-zinc-900/30 border border-zinc-800 rounded-xl py-3 pl-10 pr-4 text-sm text-zinc-400 cursor-not-allowed"
                                    />
                                    <div className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-green-500 font-bold bg-green-500/10 px-2 py-0.5 rounded-full">
                                        VERIFIED
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Bio */}
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-zinc-500 uppercase">Bio</label>
                            <textarea
                                value={bio}
                                onChange={(e) => setBio(e.target.value)}
                                disabled={!isEditing}
                                rows={4}
                                className={`
                                    w-full bg-zinc-900/50 border border-zinc-800 rounded-xl p-4 text-sm text-zinc-200 focus:outline-none transition-all resize-none
                                    ${isEditing ? 'focus:border-blue-500 focus:ring-1 focus:ring-blue-500 cursor-text' : 'opacity-60 cursor-not-allowed'}
                                `}
                            />
                        </div>

                        {/* Location & Website */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-zinc-500 uppercase">Location</label>
                                <div className="relative">
                                    <MapPin size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                                    <input
                                        type="text"
                                        value={location}
                                        onChange={(e) => setLocation(e.target.value)}
                                        disabled={!isEditing}
                                        className={`
                                            w-full bg-zinc-900/50 border border-zinc-800 rounded-xl py-3 pl-10 pr-4 text-sm text-zinc-200 focus:outline-none transition-all
                                            ${isEditing ? 'focus:border-blue-500 focus:ring-1 focus:ring-blue-500 cursor-text' : 'opacity-60 cursor-not-allowed'}
                                        `}
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-zinc-500 uppercase">Website</label>
                                <div className="relative">
                                    <LinkIcon size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                                    <input
                                        type="text"
                                        value={website}
                                        onChange={(e) => setWebsite(e.target.value)}
                                        disabled={!isEditing}
                                        className={`
                                            w-full bg-zinc-900/50 border border-zinc-800 rounded-xl py-3 pl-10 pr-4 text-sm text-zinc-200 focus:outline-none transition-all
                                            ${isEditing ? 'focus:border-blue-500 focus:ring-1 focus:ring-blue-500 cursor-text' : 'opacity-60 cursor-not-allowed'}
                                        `}
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Stats Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-zinc-800 mt-4">
                            {stats.map((stat, i) => (
                                <div key={i} className="bg-zinc-900/30 p-4 rounded-xl border border-zinc-800/50 flex flex-col gap-1">
                                    <div className="flex items-center gap-2 text-zinc-500 text-xs font-bold uppercase">
                                        {stat.icon}
                                        {stat.label}
                                    </div>
                                    <div className="text-lg font-medium text-zinc-200">{stat.value}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                </motion.div>
            </div>
        </div >
    );
}

// Sparkles icon component since it wasn't imported correctly in the list above or wanted to avoid conflicts
function SparklesIcon({ className }: { className?: string }) {
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
        >
            <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
        </svg>
    );
}
