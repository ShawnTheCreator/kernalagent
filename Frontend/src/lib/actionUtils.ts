import type { ActionType } from '@/hooks/useSocket';

// Action type to visual style mapping
export interface ActionStyle {
    color: string;
    bgColor: string;
    label: string;
}

// Map action types to UI styles
export function getActionStyle(actionType: ActionType): ActionStyle {
    const type = actionType.toUpperCase();

    switch (type) {
        case 'PLANNING':
            return { color: 'text-amber-400', bgColor: 'bg-amber-500/10', label: 'Planning' };

        case 'EXECUTING':
        case 'CLICKING':
        case 'TYPING':
        case 'OPENING':
            return { color: 'text-emerald-400', bgColor: 'bg-emerald-500/10', label: type.charAt(0) + type.slice(1).toLowerCase() };

        case 'OBSERVING':
            return { color: 'text-blue-400', bgColor: 'bg-blue-500/10', label: 'Observing' };

        case 'THINKING':
            return { color: 'text-violet-400', bgColor: 'bg-violet-500/10', label: 'Thinking' };

        case 'FAILED':
        case 'ERROR':
            return { color: 'text-red-400', bgColor: 'bg-red-500/10', label: 'Failed' };

        default:
            // Unknown action types get neutral gray
            return { color: 'text-zinc-400', bgColor: 'bg-zinc-500/10', label: type.charAt(0) + type.slice(1).toLowerCase() };
    }
}

// Format relative timestamp
export function formatRelativeTime(date: Date): string {
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);

    if (seconds < 5) return 'now';
    if (seconds < 60) return `${seconds}s ago`;

    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;

    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;

    return `${Math.floor(hours / 24)}d ago`;
}
