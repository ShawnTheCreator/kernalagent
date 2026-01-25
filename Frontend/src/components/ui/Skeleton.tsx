'use client';

import { ReactNode } from 'react';

// Skeleton Shimmer Base
export function Skeleton({ className = '', children }: { className?: string; children?: ReactNode }) {
    return (
        <div className={`skeleton-shimmer ${className}`}>
            {children}
        </div>
    );
}

// Skeleton Line (for text)
export function SkeletonLine({ width = '100%', height = '1rem' }: { width?: string; height?: string }) {
    return (
        <div
            className="skeleton-shimmer rounded"
            style={{ width, height }}
        />
    );
}

// Skeleton Circle (for avatars)
export function SkeletonCircle({ size = '3rem' }: { size?: string }) {
    return (
        <div
            className="skeleton-shimmer rounded-full"
            style={{ width: size, height: size }}
        />
    );
}

// Skeleton Card
export function SkeletonCard({ className = '' }: { className?: string }) {
    return (
        <div className={`skeleton-shimmer rounded-xl p-6 ${className}`}>
            <SkeletonCircle size="2.5rem" />
            <div className="mt-4 space-y-3">
                <SkeletonLine width="60%" height="1.5rem" />
                <SkeletonLine width="100%" height="0.875rem" />
                <SkeletonLine width="80%" height="0.875rem" />
            </div>
        </div>
    );
}

// Skeleton Bento Grid
export function SkeletonBentoGrid() {
    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 md:row-span-2">
                <SkeletonCard className="h-full min-h-[300px]" />
            </div>
            <SkeletonCard className="h-[150px]" />
            <SkeletonCard className="h-[150px]" />
            <SkeletonCard className="h-[150px]" />
            <SkeletonCard className="h-[150px]" />
            <SkeletonCard className="h-[150px]" />
        </div>
    );
}

// Skeleton Hero
export function SkeletonHero() {
    return (
        <div className="flex flex-col items-center justify-center min-h-screen px-6">
            <SkeletonLine width="200px" height="2rem" />
            <div className="mt-8 space-y-4 text-center">
                <SkeletonLine width="80%" height="4rem" />
                <SkeletonLine width="60%" height="4rem" />
            </div>
            <div className="mt-8">
                <SkeletonLine width="400px" height="1.25rem" />
            </div>
            <div className="mt-10 flex gap-4">
                <div className="skeleton-shimmer rounded-full w-48 h-14" />
                <div className="skeleton-shimmer rounded-full w-32 h-14" />
            </div>
        </div>
    );
}

// Skeleton Stats
export function SkeletonStats() {
    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 py-16">
            {[1, 2, 3, 4].map((i) => (
                <div key={i} className="flex flex-col items-center">
                    <SkeletonLine width="120px" height="3rem" />
                    <SkeletonLine width="80px" height="0.75rem" />
                </div>
            ))}
        </div>
    );
}
