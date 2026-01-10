'use client';

import type { Transition, Variants } from 'framer-motion';

// Shared Framer Motion animation presets for the dashboard
// Philosophy: "High-end system UI, not marketing animation"

// Custom easing curve (easeOutCubic)
export const easeOutCubic = [0.33, 1, 0.68, 1] as const;

// Fade in from below - used for new activity items
export const fadeInUp = {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -4 },
    transition: { duration: 0.4, ease: 'easeOut' } as Transition
};

// Subtle fade - used for panels appearing
export const fadeIn = {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    transition: { duration: 0.5, ease: 'easeOut' } as Transition
};

// Scale pulse - used for action badges (once)
export const pulse = {
    scale: [1, 1.05, 1],
    transition: { duration: 0.3, ease: 'easeOut' } as Transition
};

// Stagger children - used for lists
export const staggerContainer: Variants = {
    initial: {},
    animate: {
        transition: {
            staggerChildren: 0.05
        }
    }
};

// Count up animation config
export const countUpConfig = {
    duration: 1.5,
    ease: 'easeOut'
};

// Hover state for interactive elements
export const hoverBrighten = {
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    transition: { duration: 0.2 }
};

// Subtle glow pulse for status indicators
export const statusPulse = {
    opacity: [0.6, 1, 0.6],
    scale: [0.95, 1, 0.95],
    transition: {
        duration: 2,
        repeat: Infinity,
        ease: 'easeInOut'
    }
};

