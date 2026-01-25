/**
 * Agent Event Types
 * 
 * Normalized event structure for frontend consumption.
 * Raw backend messages are transformed into this format.
 */

// Connection states for the WebSocket
export type ConnectionState = 'CONNECTING' | 'LIVE' | 'RECONNECTING' | 'DISCONNECTED';

// Agent phases derived from backend action_type
export type AgentPhase = 'PLANNING' | 'THINKING' | 'EXECUTING' | 'OBSERVING';

// Specific action types for granular badge colors
export type ActionType =
    | 'CLICK'
    | 'TYPE'
    | 'SCROLL'
    | 'WAIT'
    | 'ERROR'
    | 'PLANNING'
    | 'THINKING'
    | 'OBSERVING'
    | 'EXECUTING'
    | 'UNKNOWN';

// Normalized event structure
export interface AgentEvent {
    id: string;
    phase: AgentPhase;
    actionType: ActionType;  // Specific action for badge color
    label: string;
    description?: string;
    timestamp: number;
}

// Raw backend message format
export interface RawBackendMessage {
    type: string;
    payload?: {
        action_type?: string;
        explanation?: string;
        [key: string]: unknown;
    };
}

// Action styling configuration
export interface ActionStyle {
    color: string;
    bgColor: string;
    label: string;
}

// Action-specific styles per user spec:
// CLICK = Blue, TYPE = Purple, SCROLL = Orange, WAIT = Gray, ERROR = Red
export const ACTION_STYLES: Record<ActionType, ActionStyle> = {
    CLICK: { color: 'text-blue-400', bgColor: 'bg-blue-500/10', label: 'Click' },
    TYPE: { color: 'text-violet-400', bgColor: 'bg-violet-500/10', label: 'Type' },
    SCROLL: { color: 'text-orange-400', bgColor: 'bg-orange-500/10', label: 'Scroll' },
    WAIT: { color: 'text-zinc-400', bgColor: 'bg-zinc-500/10', label: 'Wait' },
    ERROR: { color: 'text-red-400', bgColor: 'bg-red-500/10', label: 'Error' },
    PLANNING: { color: 'text-amber-400', bgColor: 'bg-amber-500/10', label: 'Planning' },
    THINKING: { color: 'text-violet-400', bgColor: 'bg-violet-500/10', label: 'Thinking' },
    OBSERVING: { color: 'text-blue-400', bgColor: 'bg-blue-500/10', label: 'Observing' },
    EXECUTING: { color: 'text-emerald-400', bgColor: 'bg-emerald-500/10', label: 'Executing' },
    UNKNOWN: { color: 'text-zinc-400', bgColor: 'bg-zinc-500/10', label: 'Action' },
};

// Phase style map (kept for backwards compatibility)
export const PHASE_STYLES: Record<AgentPhase, ActionStyle> = {
    EXECUTING: ACTION_STYLES.EXECUTING,
    THINKING: ACTION_STYLES.THINKING,
    PLANNING: ACTION_STYLES.PLANNING,
    OBSERVING: ACTION_STYLES.OBSERVING,
};
