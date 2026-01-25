import { create } from 'zustand';

// Agent status types
export type AgentStatus = 'live' | 'idle' | 'offline';
export type ActivityState = 'THINKING' | 'OBSERVING' | 'PLANNING' | 'EXECUTING' | 'ERROR' | 'IDLE';

// Activity event type
export interface ActivityEvent {
    id: string;
    state: ActivityState;
    title: string;
    description?: string;
    timestamp: Date;
    duration?: number;
    isNew?: boolean;
}

// Skill type
export interface Skill {
    id: string;
    name: string;
    description: string;
    confidence: 'low' | 'medium' | 'high';
    lastExecuted?: Date;
    executionCount: number;
}

// Dashboard state interface
interface DashboardState {
    // Agent state
    agentStatus: AgentStatus;
    currentState: ActivityState;
    latencyMs: number;
    sessionStartTime: Date;

    // System info
    os: string;
    version: string;
    visionEnabled: boolean;
    mouseEnabled: boolean;
    keyboardEnabled: boolean;

    // UI state
    sidebarCollapsed: boolean;
    activePanelId: string | null;

    // Data
    activities: ActivityEvent[];
    skills: Skill[];

    // Metrics
    tasksToday: number;
    avgTaskDuration: number;
    visionCalls: number;
    successRate: number;
    learningEvents: number;

    // Settings
    theme: 'dark' | 'light';
    telemetryEnabled: boolean;
    visionSensitivity: number;
    executionSpeed: number;

    // Actions
    toggleSidebar: () => void;
    setActivePanel: (id: string | null) => void;
    addActivity: (event: Omit<ActivityEvent, 'id' | 'timestamp' | 'isNew'>) => void;
    setAgentStatus: (status: AgentStatus) => void;
    updateSettings: (settings: Partial<Pick<DashboardState, 'theme' | 'telemetryEnabled' | 'visionSensitivity' | 'executionSpeed'>>) => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
    // Agent state
    agentStatus: 'live',
    currentState: 'IDLE',
    latencyMs: 42,
    sessionStartTime: new Date(),

    // System info
    os: 'Windows 11',
    version: 'v0.1.2-alpha',
    visionEnabled: true,
    mouseEnabled: true,
    keyboardEnabled: true,

    // UI state
    sidebarCollapsed: false,
    activePanelId: null,

    // Data
    activities: [],
    skills: [],

    // Metrics
    tasksToday: 247,
    avgTaskDuration: 3.2,
    visionCalls: 1842,
    successRate: 98.7,
    learningEvents: 12,

    // Settings
    theme: 'dark',
    telemetryEnabled: true,
    visionSensitivity: 75,
    executionSpeed: 50,

    // Actions
    toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

    setActivePanel: (id) => set({ activePanelId: id }),

    addActivity: (event) => {
        const newEvent: ActivityEvent = {
            ...event,
            id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            timestamp: new Date(),
            isNew: true,
        };

        set((state) => ({
            activities: [newEvent, ...state.activities].slice(0, 100),
            currentState: event.state,
        }));

        // Mark as not new after animation
        setTimeout(() => {
            set((state) => ({
                activities: state.activities.map((a) =>
                    a.id === newEvent.id ? { ...a, isNew: false } : a
                ),
            }));
        }, 300);
    },

    setAgentStatus: (status) => set({ agentStatus: status }),

    updateSettings: (settings) => set(settings),
}));
