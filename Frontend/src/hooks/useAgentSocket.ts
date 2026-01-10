'use client';

/**
 * useAgentSocket - Production-grade WebSocket hook for AI Agent Dashboard
 * 
 * Features:
 * - Auto-connect on mount
 * - Exponential backoff reconnection (1s → 2s → 4s → 8s → max 30s)
 * - Connection state tracking (CONNECTING, LIVE, RECONNECTING, DISCONNECTED)
 * - Event normalization and deduplication
 * - Message throttling to prevent UI lag during rapid bursts
 * - FIFO buffer with 50 event limit
 * - Clean unmount handling
 * 
 * Usage:
 * ```tsx
 * const { events, connectionState, isLive } = useAgentSocket();
 * ```
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { AgentEvent, ConnectionState } from '@/types/agentEvents';
import { normalizeEvent, addEventToBuffer } from '@/lib/eventNormalizer';

// Configuration
const WS_URL = 'ws://localhost:8000/ws/stream';
const MAX_EVENTS = 50;
const INITIAL_RECONNECT_DELAY = 1000;   // 1 second
const MAX_RECONNECT_DELAY = 30000;      // 30 seconds
const RECONNECT_MULTIPLIER = 2;         // Exponential backoff multiplier
const THROTTLE_INTERVAL_MS = 100;       // Minimum ms between UI updates

interface UseAgentSocketReturn {
    /** Normalized event buffer (newest first) */
    events: AgentEvent[];
    /** Current connection state */
    connectionState: ConnectionState;
    /** Shorthand for connectionState === 'LIVE' */
    isLive: boolean;
    /** Manually trigger reconnection */
    reconnect: () => void;
}

export function useAgentSocket(): UseAgentSocketReturn {
    // State
    const [events, setEvents] = useState<AgentEvent[]>([]);
    const [connectionState, setConnectionState] = useState<ConnectionState>('CONNECTING');

    // Refs for mutable values that shouldn't trigger re-renders
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY);
    const mountedRef = useRef(true);
    const reconnectAttemptsRef = useRef(0);

    // Throttling refs
    const pendingEventsRef = useRef<AgentEvent[]>([]);
    const throttleTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const lastUpdateTimeRef = useRef<number>(0);

    /**
     * Flush pending events to state (throttled)
     */
    const flushPendingEvents = useCallback(() => {
        if (!mountedRef.current) return;
        if (pendingEventsRef.current.length === 0) return;

        const eventsToAdd = pendingEventsRef.current;
        pendingEventsRef.current = [];

        setEvents(prev => {
            let newBuffer = prev;
            for (const event of eventsToAdd) {
                newBuffer = addEventToBuffer(newBuffer, event, MAX_EVENTS);
            }
            return newBuffer;
        });

        lastUpdateTimeRef.current = Date.now();
    }, []);

    /**
     * Add event with throttling to prevent UI lag
     */
    const addEventThrottled = useCallback((event: AgentEvent) => {
        pendingEventsRef.current.push(event);

        const now = Date.now();
        const timeSinceLastUpdate = now - lastUpdateTimeRef.current;

        // If enough time has passed, flush immediately
        if (timeSinceLastUpdate >= THROTTLE_INTERVAL_MS) {
            if (throttleTimeoutRef.current) {
                clearTimeout(throttleTimeoutRef.current);
                throttleTimeoutRef.current = null;
            }
            flushPendingEvents();
        } else {
            // Schedule a flush if not already scheduled
            if (!throttleTimeoutRef.current) {
                const delay = THROTTLE_INTERVAL_MS - timeSinceLastUpdate;
                throttleTimeoutRef.current = setTimeout(() => {
                    throttleTimeoutRef.current = null;
                    flushPendingEvents();
                }, delay);
            }
        }
    }, [flushPendingEvents]);

    /**
     * Calculate next reconnect delay with exponential backoff
     */
    const getNextReconnectDelay = useCallback((): number => {
        const delay = reconnectDelayRef.current;
        reconnectDelayRef.current = Math.min(
            delay * RECONNECT_MULTIPLIER,
            MAX_RECONNECT_DELAY
        );
        return delay;
    }, []);

    /**
     * Reset reconnection state after successful connection
     */
    const resetReconnectState = useCallback(() => {
        reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
        reconnectAttemptsRef.current = 0;
    }, []);

    /**
     * Clear any pending reconnection timeout
     */
    const clearReconnectTimeout = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
    }, []);

    /**
     * Close the WebSocket connection cleanly
     */
    const closeConnection = useCallback(() => {
        clearReconnectTimeout();
        if (throttleTimeoutRef.current) {
            clearTimeout(throttleTimeoutRef.current);
            throttleTimeoutRef.current = null;
        }
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
    }, [clearReconnectTimeout]);

    /**
     * Schedule a reconnection attempt
     */
    const scheduleReconnect = useCallback((connect: () => void) => {
        if (!mountedRef.current) return;

        clearReconnectTimeout();

        const delay = getNextReconnectDelay();
        reconnectAttemptsRef.current += 1;

        console.log(
            `[useAgentSocket] Scheduling reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current})`
        );

        reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current) {
                connect();
            }
        }, delay);
    }, [clearReconnectTimeout, getNextReconnectDelay]);

    /**
     * Connect to WebSocket server
     */
    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN ||
            wsRef.current?.readyState === WebSocket.CONNECTING) {
            return;
        }

        if (reconnectAttemptsRef.current > 0) {
            setConnectionState('RECONNECTING');
        } else {
            setConnectionState('CONNECTING');
        }

        try {
            const ws = new WebSocket(WS_URL);
            wsRef.current = ws;

            ws.onopen = () => {
                if (!mountedRef.current) return;
                console.log('[useAgentSocket] Connected to', WS_URL);
                setConnectionState('LIVE');
                resetReconnectState();
            };

            ws.onmessage = (event) => {
                if (!mountedRef.current) return;

                const normalizedEvent = normalizeEvent(event.data);
                if (normalizedEvent) {
                    addEventThrottled(normalizedEvent);
                }
            };

            ws.onclose = (event) => {
                if (!mountedRef.current) return;

                console.log(
                    `[useAgentSocket] Connection closed (code: ${event.code}, reason: ${event.reason || 'none'})`
                );

                wsRef.current = null;

                if (event.code !== 1000) {
                    setConnectionState('RECONNECTING');
                    scheduleReconnect(connect);
                } else {
                    setConnectionState('DISCONNECTED');
                }
            };

            ws.onerror = () => {
                if (!mountedRef.current) return;
                console.warn('[useAgentSocket] Connection error occurred');
            };

        } catch (error) {
            console.error('[useAgentSocket] Failed to create WebSocket:', error);
            setConnectionState('DISCONNECTED');
            scheduleReconnect(connect);
        }
    }, [resetReconnectState, scheduleReconnect, addEventThrottled]);

    /**
     * Manual reconnect function exposed to consumers
     */
    const reconnect = useCallback(() => {
        closeConnection();
        resetReconnectState();
        connect();
    }, [closeConnection, resetReconnectState, connect]);

    // Setup and cleanup
    useEffect(() => {
        mountedRef.current = true;
        connect();

        return () => {
            mountedRef.current = false;
            closeConnection();
            // Flush any remaining events
            flushPendingEvents();
        };
    }, [connect, closeConnection, flushPendingEvents]);

    return {
        events,
        connectionState,
        isLive: connectionState === 'LIVE',
        reconnect,
    };
}

export default useAgentSocket;
