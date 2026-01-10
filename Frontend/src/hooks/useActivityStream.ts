'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

export interface ActivityEvent {
    id: string;
    type: 'action';
    payload: {
        explanation: string;
        action_type: 'CLICKING' | 'TYPING' | 'OPENING_APP' | 'THINKING' | 'SCROLLING' | 'NAVIGATING' | 'READING' | 'EXECUTING';
    };
    timestamp: Date;
    isNew?: boolean;
}

interface UseActivityStreamOptions {
    url?: string;
    maxItems?: number;
    reconnectInterval?: number;
}

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export function useActivityStream(options: UseActivityStreamOptions = {}) {
    const {
        url = 'ws://localhost:8000/ws/stream',
        maxItems = 50,
        reconnectInterval = 3000
    } = options;

    const [activities, setActivities] = useState<ActivityEvent[]>([]);
    const [status, setStatus] = useState<ConnectionStatus>('disconnected');
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        setStatus('connecting');

        try {
            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                setStatus('connected');
                if (reconnectTimeoutRef.current) {
                    clearTimeout(reconnectTimeoutRef.current);
                    reconnectTimeoutRef.current = null;
                }
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.type === 'action') {
                        const newActivity: ActivityEvent = {
                            id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                            type: data.type,
                            payload: data.payload,
                            timestamp: new Date(),
                            isNew: true
                        };

                        setActivities((prev) => {
                            const updated = [newActivity, ...prev].slice(0, maxItems);
                            // Mark items as not new after a short delay
                            setTimeout(() => {
                                setActivities((current) =>
                                    current.map((item) =>
                                        item.id === newActivity.id ? { ...item, isNew: false } : item
                                    )
                                );
                            }, 500);
                            return updated;
                        });
                    }
                } catch (err) {
                    console.error('Failed to parse WebSocket message:', err);
                }
            };

            ws.onclose = () => {
                setStatus('disconnected');
                wsRef.current = null;

                // Auto-reconnect
                reconnectTimeoutRef.current = setTimeout(() => {
                    connect();
                }, reconnectInterval);
            };

            ws.onerror = () => {
                setStatus('error');
            };
        } catch (err) {
            setStatus('error');
            console.error('WebSocket connection error:', err);
        }
    }, [url, maxItems, reconnectInterval]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        setStatus('disconnected');
    }, []);

    const refresh = useCallback(() => {
        disconnect();
        connect();
    }, [connect, disconnect]);

    // Connect on mount
    useEffect(() => {
        connect();
        return () => disconnect();
    }, [connect, disconnect]);

    // Demo mode: Generate fake activities if no WebSocket
    useEffect(() => {
        if (status === 'error' || status === 'disconnected') {
            // Generate demo data after a short delay
            const demoTimeout = setTimeout(() => {
                const demoActivities: ActivityEvent[] = [
                    {
                        id: 'demo-1',
                        type: 'action',
                        payload: { explanation: 'Analyzing user request...', action_type: 'THINKING' },
                        timestamp: new Date(Date.now() - 2000),
                        isNew: false
                    },
                    {
                        id: 'demo-2',
                        type: 'action',
                        payload: { explanation: 'Opening Notepad application', action_type: 'OPENING_APP' },
                        timestamp: new Date(Date.now() - 5000),
                        isNew: false
                    },
                    {
                        id: 'demo-3',
                        type: 'action',
                        payload: { explanation: 'Typing document content', action_type: 'TYPING' },
                        timestamp: new Date(Date.now() - 8000),
                        isNew: false
                    },
                    {
                        id: 'demo-4',
                        type: 'action',
                        payload: { explanation: 'Clicking save button', action_type: 'CLICKING' },
                        timestamp: new Date(Date.now() - 12000),
                        isNew: false
                    },
                ];
                setActivities(demoActivities);
            }, 1000);

            return () => clearTimeout(demoTimeout);
        }
    }, [status]);

    return {
        activities,
        status,
        connect,
        disconnect,
        refresh,
        isConnected: status === 'connected'
    };
}
