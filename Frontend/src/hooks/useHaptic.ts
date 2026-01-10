'use client';

import { useCallback } from 'react';

type HapticPattern = 'light' | 'medium' | 'heavy' | 'success' | 'error';

const PATTERNS: Record<HapticPattern, number[]> = {
    light: [10],
    medium: [25],
    heavy: [50],
    success: [10, 50, 10],
    error: [50, 30, 50, 30, 50],
};

export function useHaptic() {
    const vibrate = useCallback((pattern: HapticPattern = 'light') => {
        if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
            navigator.vibrate(PATTERNS[pattern]);
        }
    }, []);

    const triggerTap = useCallback(() => vibrate('light'), [vibrate]);
    const triggerSuccess = useCallback(() => vibrate('success'), [vibrate]);
    const triggerError = useCallback(() => vibrate('error'), [vibrate]);

    return {
        vibrate,
        triggerTap,
        triggerSuccess,
        triggerError,
    };
}
