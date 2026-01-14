'use client';

/**
 * Firebase Auth Context
 * 
 * Provides authentication state and methods throughout the app.
 * Replaces localStorage-based auth with Firebase Authentication.
 */
import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import {
    User,
    onAuthStateChanged,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signOut,
    signInWithPopup,
    updateProfile,
} from 'firebase/auth';
import { auth, googleProvider, githubProvider } from '@/lib/firebase';

// Auth context type
interface AuthContextType {
    user: User | null;
    loading: boolean;
    error: string | null;
    login: (email: string, password: string) => Promise<void>;
    signup: (email: string, password: string, name: string) => Promise<void>;
    logout: () => Promise<void>;
    loginWithGoogle: () => Promise<void>;
    loginWithGithub: () => Promise<void>;
    updateUser: (profile: { displayName?: string; photoURL?: string }) => Promise<void>;
    clearError: () => void;
}

// Create context with null default
const AuthContext = createContext<AuthContextType | null>(null);

// Auth Provider component
export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // API base URL for backend (uses Render URL in production)
    const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URLCSHARP || 'https://kernal-agent-backend.onrender.com').replace(/\/+$/, '');

    // Sync user to Firestore via backend API
    const syncUserToFirestore = async (user: User) => {
        try {
            const token = await user.getIdToken();
            const response = await fetch(`${API_BASE}/api/auth/me`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });
            if (response.ok) {
                console.log('[AUTH] User synced to Firestore successfully');
            } else {
                console.warn('[AUTH] Failed to sync user to Firestore:', response.status);
            }
        } catch (error) {
            console.warn('[AUTH] Error syncing user to Firestore:', error);
            // Don't throw - this is a background sync, not critical for auth flow
        }
    };

    // Listen to Firebase auth state changes
    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, async (user) => {
            setUser(user);
            setLoading(false);

            // Sync user to Firestore backend when logged in
            if (user) {
                syncUserToFirestore(user);
            }
        });

        // Cleanup subscription
        return () => unsubscribe();
    }, []);

    // Email/password login
    const login = async (email: string, password: string) => {
        setError(null);
        try {
            await signInWithEmailAndPassword(auth, email, password);
        } catch (err: any) {
            const message = getFirebaseErrorMessage(err.code);
            setError(message);
            throw new Error(message);
        }
    };

    // Email/password signup
    const signup = async (email: string, password: string, name: string) => {
        setError(null);
        try {
            const result = await createUserWithEmailAndPassword(auth, email, password);
            // Update profile with display name
            if (result.user) {
                await updateProfile(result.user, { displayName: name });
            }
        } catch (err: any) {
            const message = getFirebaseErrorMessage(err.code);
            setError(message);
            throw new Error(message);
        }
    };

    // Update User Profile
    const updateUser = async (profile: { displayName?: string; photoURL?: string }) => {
        if (!auth.currentUser) return;
        try {
            await updateProfile(auth.currentUser, profile);

            // Reload user to get fresh data
            await auth.currentUser.reload();

            // Force local state update while preserving prototype methods
            // We create a new object reference that inherits from the same prototype
            const currentUser = auth.currentUser;
            const updatedUser = Object.assign(
                Object.create(Object.getPrototypeOf(currentUser)),
                currentUser
            );

            setUser(updatedUser);
        } catch (err) {
            console.error('Failed to update profile', err);
            throw err;
        }
    };

    // Logout
    const logout = async () => {
        setError(null);
        try {
            await signOut(auth);
        } catch (err: any) {
            setError('Failed to logout');
            throw err;
        }
    };

    // Google OAuth login
    const loginWithGoogle = async () => {
        setError(null);
        try {
            await signInWithPopup(auth, googleProvider);
        } catch (err: any) {
            const message = getFirebaseErrorMessage(err.code);
            setError(message);
            throw new Error(message);
        }
    };

    // GitHub OAuth login
    const loginWithGithub = async () => {
        setError(null);
        try {
            await signInWithPopup(auth, githubProvider);
        } catch (err: any) {
            const message = getFirebaseErrorMessage(err.code);
            setError(message);
            throw new Error(message);
        }
    };

    // Clear error
    const clearError = () => setError(null);

    const value: AuthContextType = {
        user,
        loading,
        error,
        login,
        signup,
        updateUser,
        logout,
        loginWithGoogle,
        loginWithGithub,
        clearError,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Custom hook to use auth context
export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}

// Helper: Convert Firebase error codes to user-friendly messages
function getFirebaseErrorMessage(code: string): string {
    switch (code) {
        case 'auth/email-already-in-use':
            return 'This email is already registered';
        case 'auth/invalid-email':
            return 'Invalid email address';
        case 'auth/user-disabled':
            return 'This account has been disabled';
        case 'auth/user-not-found':
            return 'No account found with this email';
        case 'auth/wrong-password':
            return 'Incorrect password';
        case 'auth/invalid-credential':
            return 'Invalid email or password';
        case 'auth/weak-password':
            return 'Password should be at least 6 characters';
        case 'auth/popup-closed-by-user':
            return 'Sign-in popup was closed';
        case 'auth/cancelled-popup-request':
            return 'Only one popup request allowed at a time';
        case 'auth/account-exists-with-different-credential':
            return 'An account already exists with this email using a different sign-in method';
        default:
            return 'An error occurred. Please try again.';
    }
}
