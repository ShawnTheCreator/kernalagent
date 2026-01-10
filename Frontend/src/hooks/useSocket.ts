'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

// WebSocket URL
const WS_URL = 'ws://localhost:8000/ws/stream';

// Action types from backend
export type ActionType =
    | 'PLANNING'
    | 'EXECUTING'
    | 'OBSERVING'
    | 'THINKING'
    | 'FAILED'
    | 'CLICKING'
    | 'TYPING'
    | 'OPENING'
    | string; // Allow unknown types

// Incoming action message structure
export interface ActionMessage {
    id: string;
    action_type: ActionType;
    explanation: string;
    timestamp: Date;
    isNew?: boolean;
}

// WebSocket connection status
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

// Hook return type
interface UseSocketReturn {
    actions: ActionMessage[];
    status: ConnectionStatus;
    isConnected: boolean;
}

// Maximum actions to keep in memory
const MAX_ACTIONS = 50;

// Reconnect delay in ms
const RECONNECT_DELAY = 3000;

export function useSocket(): UseSocketReturn {
    const [actions, setActions] = useState<ActionMessage[]>([]);
    const [status, setStatus] = useState<ConnectionStatus>('connecting');

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const mountedRef = useRef(true);

    // Parse incoming message safely
    const parseMessage = useCallback((data: string): ActionMessage | null => {
        try {
            const parsed = JSON.parse(data);

            // Only handle action messages
            if (parsed.type !== 'action' || !parsed.payload) {
                return null;
            }

            const { action_type, explanation, timestamp } = parsed.payload;

            // Validate required fields
            if (!action_type || !explanation) {
                return null;
            }

            return {
                id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                action_type: action_type.toUpperCase(),
                explanation,
                timestamp: timestamp ? new Date(timestamp) : new Date(),
                isNew: true,
            };
        } catch (e) {
            console.warn('[useSocket] Failed to parse message:', e);
            return null;
        }
    }, []);

    // Add action to state
    const addAction = useCallback((action: ActionMessage) => {
        setActions(prev => {
            const updated = [action, ...prev].slice(0, MAX_ACTIONS);
            return updated;
        });

        // Remove "isNew" flag after animation
        setTimeout(() => {
            if (!mountedRef.current) return;
            setActions(prev =>
                prev.map(a => a.id === action.id ? { ...a, isNew: false } : a)
            );
        }, 500);
    }, []);

    // Connect to WebSocket
    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        setStatus('connecting');

        try {
            const ws = new WebSocket(WS_URL);
            wsRef.current = ws;

            ws.onopen = () => {
                if (!mountedRef.current) return;
                console.log('[useSocket] Connected to', WS_URL);
                setStatus('connected');
            };

            ws.onmessage = (event) => {
                if (!mountedRef.current) return;
                const action = parseMessage(event.data);
                if (action) {
                    addAction(action);
                }
            };

            ws.onclose = () => {
                if (!mountedRef.current) return;
                console.log('[useSocket] Disconnected, will reconnect...');
                setStatus('disconnected');

                // Schedule reconnect
                reconnectTimeoutRef.current = setTimeout(() => {
                    if (mountedRef.current) {
                        connect();
                    }
                }, RECONNECT_DELAY);
            };

            ws.onerror = (error) => {
                if (!mountedRef.current) return;
                console.error('[useSocket] Error:', error);
                setStatus('error');
            };

        } catch (error) {
            console.error('[useSocket] Failed to connect:', error);
            setStatus('error');

            // Retry connection
            reconnectTimeoutRef.current = setTimeout(() => {
                if (mountedRef.current) {
                    connect();
                }
            }, RECONNECT_DELAY);
        }
    }, [parseMessage, addAction]);

    // Setup WebSocket on mount
    useEffect(() => {
        mountedRef.current = true;
        connect();

        return () => {
            mountedRef.current = false;

            // Cleanup timeout
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }

            // Close WebSocket
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [connect]);

    return {
        actions,
        status,
        isConnected: status === 'connected',
    };
}
