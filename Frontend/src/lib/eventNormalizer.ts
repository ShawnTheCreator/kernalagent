/**
 * Event Normalizer
 * 
 * Transforms raw backend WebSocket messages into normalized AgentEvent format.
 * Handles mapping of action_type to phase and generates client-side IDs.
 */

import type { AgentEvent, AgentPhase, ActionType, RawBackendMessage } from '@/types/agentEvents';

// Action type to phase mapping
const ACTION_TO_PHASE: Record<string, AgentPhase> = {
    // Planning phase
    'PLANNING': 'PLANNING',
    'PLAN': 'PLANNING',

    // Thinking phase
    'THINKING': 'THINKING',
    'ANALYZING': 'THINKING',
    'REASONING': 'THINKING',

    // Executing phase - all active actions
    'EXECUTING': 'EXECUTING',
    'CLICKING': 'EXECUTING',
    'CLICK': 'EXECUTING',
    'TYPING': 'EXECUTING',
    'TYPE': 'EXECUTING',
    'SCROLLING': 'EXECUTING',
    'SCROLL': 'EXECUTING',
    'OPENING': 'EXECUTING',
    'OPEN': 'EXECUTING',
    'NAVIGATING': 'EXECUTING',
    'READING': 'EXECUTING',
    'WAIT': 'EXECUTING',
    'WAITING': 'EXECUTING',

    // Skill execution
    'SKILL_START': 'EXECUTING',
    'SKILL_COMPLETE': 'EXECUTING',
    'SKILL_FAILED': 'THINKING',
    'SKILL_ERROR': 'THINKING',
    'RUNNING SKILL': 'EXECUTING',
    'ACTION': 'EXECUTING',

    // Observing phase
    'OBSERVING': 'OBSERVING',
    'OBSERVE': 'OBSERVING',
    'WATCHING': 'OBSERVING',
    'CAPTURING': 'OBSERVING',

    // Idle
    'IDLE': 'OBSERVING',

    // Error states
    'ERROR': 'THINKING',
    'FAILED': 'THINKING',
};

// Action type to specific ActionType for badge colors
const ACTION_TO_TYPE: Record<string, ActionType> = {
    // Click actions -> Blue
    'CLICK': 'CLICK',
    'CLICKING': 'CLICK',

    // Type actions -> Purple
    'TYPE': 'TYPE',
    'TYPING': 'TYPE',

    // Scroll actions -> Orange
    'SCROLL': 'SCROLL',
    'SCROLLING': 'SCROLL',

    // Wait actions -> Gray
    'WAIT': 'WAIT',
    'WAITING': 'WAIT',

    // Error actions -> Red
    'ERROR': 'ERROR',
    'FAILED': 'ERROR',

    // Phase-based fallbacks
    'PLANNING': 'PLANNING',
    'PLAN': 'PLANNING',
    'THINKING': 'THINKING',
    'ANALYZING': 'THINKING',
    'OBSERVING': 'OBSERVING',
    'OBSERVE': 'OBSERVING',
    'EXECUTING': 'EXECUTING',
    'OPENING': 'EXECUTING',
    'OPEN': 'EXECUTING',
    'NAVIGATING': 'EXECUTING',
    'READING': 'OBSERVING',
};

const DEFAULT_PHASE: AgentPhase = 'OBSERVING';
const DEFAULT_ACTION_TYPE: ActionType = 'UNKNOWN';

let idCounter = 0;

/**
 * Generate a unique client-side ID for events
 */
function generateEventId(): string {
    idCounter = (idCounter + 1) % Number.MAX_SAFE_INTEGER;
    return `evt_${Date.now()}_${idCounter.toString(36)}`;
}

/**
 * Map backend action_type to frontend phase
 */
export function mapActionToPhase(actionType: string): AgentPhase {
    const normalized = actionType.toUpperCase().trim();
    return ACTION_TO_PHASE[normalized] ?? DEFAULT_PHASE;
}

/**
 * Map backend action_type to specific ActionType for badge colors
 */
export function mapActionToType(actionType: string): ActionType {
    const normalized = actionType.toUpperCase().trim();
    return ACTION_TO_TYPE[normalized] ?? DEFAULT_ACTION_TYPE;
}

/**
 * Validate that a message is an action message from the backend
 */
export function isActionMessage(data: unknown): boolean {
    if (typeof data !== 'object' || data === null) return false;

    const msg = data as Record<string, unknown>;
    // Accept both 'action' (from vision) and 'action_executed' (from C# brain)
    return (
        (msg.type === 'action' && typeof msg.payload === 'object') ||
        (msg.type === 'action_executed') ||
        (msg.type === 'agent_state')
    );
}

/**
 * Parse raw JSON string from WebSocket into object
 */
export function parseMessage(data: string): unknown | null {
    try {
        return JSON.parse(data);
    } catch {
        console.warn('[eventNormalizer] Failed to parse message:', data.slice(0, 100));
        return null;
    }
}

/**
 * Normalize a raw backend message into an AgentEvent
 * Returns null if the message is not a valid action message
 */
export function normalizeEvent(data: string): AgentEvent | null {
    const parsed = parseMessage(data);
    if (!parsed || !isActionMessage(parsed)) {
        return null;
    }

    const msg = parsed as Record<string, unknown>;
    const msgType = msg.type as string;

    // Handle action_executed from C# brain connection
    if (msgType === 'action_executed') {
        const state = (msg.state as string) || 'EXECUTING';
        const title = (msg.title as string) || 'Action';
        const description = (msg.description as string) || '';
        const action = msg.action as Record<string, unknown> | undefined;

        const actionType = action?.action_type as string || title.toUpperCase();

        return {
            id: generateEventId(),
            phase: mapActionToPhase(state),
            actionType: mapActionToType(actionType),
            label: title,
            description: description,
            timestamp: Date.now(),
        };
    }

    // Handle agent_state updates
    if (msgType === 'agent_state') {
        const state = (msg.state as string) || 'OBSERVING';
        const title = (msg.title as string) || 'Agent State';
        const description = (msg.description as string) || '';

        return {
            id: generateEventId(),
            phase: mapActionToPhase(state),
            actionType: mapActionToType(state),
            label: title,
            description: description,
            timestamp: Date.now(),
        };
    }

    // Handle original 'action' messages from vision analysis
    const payload = msg.payload as Record<string, unknown> | undefined;
    if (!payload) return null;

    const rawActionType = (payload.action_type as string) ?? 'UNKNOWN';
    const explanation = (payload.explanation as string) ?? 'Unknown action';

    return {
        id: generateEventId(),
        phase: mapActionToPhase(rawActionType),
        actionType: mapActionToType(rawActionType),
        label: explanation,
        description: typeof payload.action_type === 'string' ? payload.action_type : undefined,
        timestamp: Date.now(),
    };
}

/**
 * Check if two events are considered duplicates
 * Events are duplicates if they have the same phase and label
 */
export function isDuplicateEvent(a: AgentEvent, b: AgentEvent): boolean {
    return a.phase === b.phase && a.label === b.label;
}

/**
 * Add event to buffer with deduplication and FIFO overflow handling
 */
export function addEventToBuffer(
    buffer: AgentEvent[],
    event: AgentEvent,
    maxSize: number = 50
): AgentEvent[] {
    // Check for duplicate with most recent event
    if (buffer.length > 0 && isDuplicateEvent(buffer[0], event)) {
        // Update timestamp of existing event instead of adding duplicate
        return [
            { ...buffer[0], timestamp: event.timestamp },
            ...buffer.slice(1)
        ];
    }

    // Add to front, trim to max size (FIFO)
    const newBuffer = [event, ...buffer];
    if (newBuffer.length > maxSize) {
        return newBuffer.slice(0, maxSize);
    }

    return newBuffer;
}
