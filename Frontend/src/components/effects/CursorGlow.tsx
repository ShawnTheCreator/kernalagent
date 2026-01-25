'use client';

import { useMousePosition } from '@/hooks';

export function CursorGlow() {
    const { x, y } = useMousePosition();

    return (
        <div
            className="cursor-glow hidden lg:block"
            style={{ left: x, top: y }}
        />
    );
}
