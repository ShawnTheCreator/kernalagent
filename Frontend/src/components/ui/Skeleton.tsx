'use client';

import { cn } from '@/lib/utils';

interface SkeletonProps {
    className?: string;
    variant?: 'text' | 'card' | 'image' | 'button' | 'circle';
    animate?: boolean;
}

export function Skeleton({ className, variant = 'text', animate = true }: SkeletonProps) {
    const baseClasses = 'bg-white/5 rounded';
    const shimmerClasses = animate ? 'skeleton-shimmer' : '';

    const variantClasses = {
        text: 'h-4 w-full',
        card: 'h-32 w-full rounded-xl',
        image: 'aspect-video w-full rounded-xl',
        button: 'h-12 w-32 rounded-full',
        circle: 'h-12 w-12 rounded-full',
    };

    return (
        <div
            className={cn(baseClasses, shimmerClasses, variantClasses[variant], className)}
        />
    );
}

// Card skeleton with multiple elements
export function CardSkeleton() {
    return (
        <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6 space-y-4">
            <Skeleton variant="circle" className="h-8 w-8" />
            <Skeleton className="w-1/2" />
            <Skeleton className="w-full" />
            <Skeleton className="w-3/4" />
        </div>
    );
}

// Section skeleton
export function SectionSkeleton() {
    return (
        <div className="py-24 px-6">
            <div className="max-w-6xl mx-auto">
                <div className="text-center mb-12 space-y-4">
                    <Skeleton className="w-32 h-4 mx-auto" />
                    <Skeleton className="w-64 h-8 mx-auto" />
                </div>
                <div className="grid md:grid-cols-3 gap-6">
                    <CardSkeleton />
                    <CardSkeleton />
                    <CardSkeleton />
                </div>
            </div>
        </div>
    );
}

// Hero skeleton
export function HeroSkeleton() {
    return (
        <div className="min-h-screen flex flex-col items-center justify-center px-6 space-y-8">
            <Skeleton className="w-48 h-6 rounded-full" />
            <div className="space-y-4 text-center">
                <Skeleton className="w-[400px] h-16 mx-auto" />
                <Skeleton className="w-[300px] h-16 mx-auto" />
            </div>
            <Skeleton className="w-[500px] h-6 mx-auto" />
            <div className="flex gap-4 pt-8">
                <Skeleton variant="button" className="w-48" />
                <Skeleton className="w-32 h-12" />
            </div>
        </div>
    );
}
