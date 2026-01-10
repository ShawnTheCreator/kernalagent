'use client';

import { useCallback, useEffect, useState } from 'react';

// Haptic feedback types
type HapticType = 'light' | 'medium' | 'heavy' | 'selection' | 'success' | 'warning' | 'error';

// Check if device supports vibration
const supportsVibration = typeof window !== 'undefined' && 'vibrate' in navigator;

// Vibration patterns for different haptic types
const vibrationPatterns: Record<HapticType, number | number[]> = {
    light: 10,
    medium: 25,
    heavy: 50,
    selection: 15,
    success: [20, 50, 30],
    warning: [30, 30, 30, 30],
    error: [50, 50, 50],
};

export function useMobileInteractions() {
    const [isMobile, setIsMobile] = useState(false);
    const [isTouching, setIsTouching] = useState(false);

    useEffect(() => {
        const checkMobile = () => {
            setIsMobile(window.matchMedia('(max-width: 768px)').matches || 'ontouchstart' in window);
        };
        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    }, []);

    // Trigger haptic feedback
    const haptic = useCallback((type: HapticType = 'light') => {
        if (supportsVibration && isMobile) {
            navigator.vibrate(vibrationPatterns[type]);
        }
    }, [isMobile]);

    // Touch start handler for press effects
    const onTouchStart = useCallback(() => {
        setIsTouching(true);
        haptic('light');
    }, [haptic]);

    // Touch end handler
    const onTouchEnd = useCallback(() => {
        setIsTouching(false);
    }, []);

    // Get touch handlers for interactive elements
    const getTouchHandlers = useCallback(() => ({
        onTouchStart,
        onTouchEnd,
        onTouchCancel: onTouchEnd,
    }), [onTouchStart, onTouchEnd]);

    // Pull to refresh handler
    const usePullToRefresh = (onRefresh: () => void, threshold = 100) => {
        const [pullDistance, setPullDistance] = useState(0);
        const [isRefreshing, setIsRefreshing] = useState(false);
        let startY = 0;

        const handleTouchStart = (e: TouchEvent) => {
            if (window.scrollY === 0) {
                startY = e.touches[0].clientY;
            }
        };

        const handleTouchMove = (e: TouchEvent) => {
            if (startY === 0 || isRefreshing) return;
            const currentY = e.touches[0].clientY;
            const distance = Math.max(0, (currentY - startY) * 0.5);
            if (distance > 0) {
                setPullDistance(Math.min(distance, threshold * 1.5));
            }
        };

        const handleTouchEnd = () => {
            if (pullDistance >= threshold && !isRefreshing) {
                setIsRefreshing(true);
                haptic('success');
                onRefresh();
                setTimeout(() => {
                    setIsRefreshing(false);
                    setPullDistance(0);
                }, 1500);
            } else {
                setPullDistance(0);
            }
            startY = 0;
        };

        return { pullDistance, isRefreshing };
    };

    return {
        isMobile,
        isTouching,
        haptic,
        getTouchHandlers,
        usePullToRefresh,
    };
}

// Touch ripple effect hook
export function useTouchRipple() {
    const [ripples, setRipples] = useState<Array<{ x: number; y: number; id: number }>>([]);

    const createRipple = useCallback((e: React.TouchEvent<HTMLElement>) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const x = e.touches[0].clientX - rect.left;
        const y = e.touches[0].clientY - rect.top;
        const id = Date.now();

        setRipples((prev) => [...prev, { x, y, id }]);

        // Remove ripple after animation
        setTimeout(() => {
            setRipples((prev) => prev.filter((r) => r.id !== id));
        }, 600);
    }, []);

    const RippleContainer = () => (
        <div className= "absolute inset-0 overflow-hidden pointer-events-none" >
        {
            ripples.map(({ x, y, id }) => (
                <span
          key= { id }
          className = "absolute w-0 h-0 rounded-full bg-white/30 animate-ripple"
          style = {{
                left: x,
                top: y,
                transform: 'translate(-50%, -50%)',
            }}
        />
      ))
}
</div>
  );

return { createRipple, RippleContainer };
}

// Swipe gesture hook
export function useSwipeGesture(onSwipeLeft?: () => void, onSwipeRight?: () => void) {
    const [touchStart, setTouchStart] = useState({ x: 0, y: 0 });
    const [touchEnd, setTouchEnd] = useState({ x: 0, y: 0 });

    const minSwipeDistance = 50;

    const onTouchStart = (e: React.TouchEvent) => {
        setTouchEnd({ x: 0, y: 0 });
        setTouchStart({
            x: e.targetTouches[0].clientX,
            y: e.targetTouches[0].clientY,
        });
    };

    const onTouchMove = (e: React.TouchEvent) => {
        setTouchEnd({
            x: e.targetTouches[0].clientX,
            y: e.targetTouches[0].clientY,
        });
    };

    const onTouchEndHandler = () => {
        if (!touchStart.x || !touchEnd.x) return;

        const distanceX = touchStart.x - touchEnd.x;
        const distanceY = touchStart.y - touchEnd.y;
        const isHorizontalSwipe = Math.abs(distanceX) > Math.abs(distanceY);

        if (isHorizontalSwipe && Math.abs(distanceX) > minSwipeDistance) {
            if (distanceX > 0) {
                onSwipeLeft?.();
            } else {
                onSwipeRight?.();
            }
        }
    };

    return {
        onTouchStart,
        onTouchMove,
        onTouchEnd: onTouchEndHandler,
    };
}
