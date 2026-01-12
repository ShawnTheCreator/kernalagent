/**
 * Firebase Configuration
 * 
 * Initializes Firebase app and exports auth instance.
 * Uses environment variables for config (see .env.local).
 */
import { initializeApp, getApps, getApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, GithubAuthProvider } from 'firebase/auth';

// Firebase configuration from environment variables
const firebaseConfig = {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

// DEBUG: Log config to verify values are loaded
console.log('[FIREBASE DEBUG] Config loaded:', {
    apiKey: firebaseConfig.apiKey ? '✅ SET' : '❌ MISSING',
    authDomain: firebaseConfig.authDomain || '❌ MISSING',
    projectId: firebaseConfig.projectId || '❌ MISSING',
    storageBucket: firebaseConfig.storageBucket || '❌ MISSING',
    messagingSenderId: firebaseConfig.messagingSenderId || '❌ MISSING',
    appId: firebaseConfig.appId ? '✅ SET' : '❌ MISSING',
});

// Initialize Firebase (avoid duplicate initialization)
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApp();

// Export auth instance
export const auth = getAuth(app);

// Export OAuth providers
export const googleProvider = new GoogleAuthProvider();
export const githubProvider = new GithubAuthProvider();

export default app;
