// Mock API layer for dashboard data
// TODO: Replace with real API calls when backend is ready

import type { ActivityEvent, Skill, ActivityState } from '@/stores/dashboardStore';

// Mock activities
export const mockActivities: Omit<ActivityEvent, 'id' | 'timestamp' | 'isNew'>[] = [
    { state: 'EXECUTING', title: 'Opening Notepad', description: 'Launching application to write document' },
    { state: 'THINKING', title: 'Analyzing request', description: 'Processing user intent and planning action sequence' },
    { state: 'OBSERVING', title: 'Reading screen content', description: 'Capturing current window state' },
    { state: 'PLANNING', title: 'Determining next steps', description: 'Building execution plan for task completion' },
    { state: 'EXECUTING', title: 'Clicking save button', description: 'Executing mouse click at coordinates (842, 156)' },
    { state: 'EXECUTING', title: 'Typing content', description: 'Entering text into active field' },
];

// Mock skills
export const mockSkills: Skill[] = [
    { id: '1', name: 'Open Application', description: 'Launch any installed application by name', confidence: 'high', lastExecuted: new Date(Date.now() - 60000), executionCount: 347 },
    { id: '2', name: 'Type Text', description: 'Enter text into focused input fields', confidence: 'high', lastExecuted: new Date(Date.now() - 120000), executionCount: 892 },
    { id: '3', name: 'Click Element', description: 'Click on screen elements by visual recognition', confidence: 'high', lastExecuted: new Date(Date.now() - 30000), executionCount: 1243 },
    { id: '4', name: 'Scroll Page', description: 'Scroll within windows and web pages', confidence: 'medium', lastExecuted: new Date(Date.now() - 300000), executionCount: 156 },
    { id: '5', name: 'Navigate Tabs', description: 'Switch between browser tabs and windows', confidence: 'medium', lastExecuted: new Date(Date.now() - 600000), executionCount: 89 },
    { id: '6', name: 'Fill Form', description: 'Automatically populate form fields', confidence: 'medium', lastExecuted: new Date(Date.now() - 3600000), executionCount: 34 },
    { id: '7', name: 'Screenshot Analysis', description: 'Extract information from screen captures', confidence: 'high', lastExecuted: new Date(Date.now() - 45000), executionCount: 567 },
    { id: '8', name: 'File Management', description: 'Create, move, and organize files', confidence: 'low', lastExecuted: new Date(Date.now() - 86400000), executionCount: 12 },
];

// Mock metrics over time (last 24 hours, hourly)
export const mockMetricsHistory = {
    tasksPerHour: [12, 8, 15, 22, 18, 24, 31, 28, 19, 14, 16, 21, 25, 23, 17, 20, 26, 29, 33, 27, 22, 18, 15, 11],
    latencyMs: [45, 42, 48, 51, 39, 44, 47, 52, 41, 38, 43, 46, 49, 44, 40, 42, 45, 48, 51, 47, 43, 41, 39, 42],
    successRate: [100, 98, 99, 97, 100, 99, 98, 99, 100, 98, 99, 100, 97, 99, 100, 98, 99, 100, 98, 99, 100, 99, 98, 100],
};

// Simulate real-time activity
export function startActivitySimulation(addActivity: (event: Omit<ActivityEvent, 'id' | 'timestamp' | 'isNew'>) => void) {
    const states: ActivityState[] = ['THINKING', 'OBSERVING', 'PLANNING', 'EXECUTING'];
    const titles: Record<ActivityState, string[]> = {
        THINKING: ['Analyzing request', 'Processing context', 'Evaluating options'],
        OBSERVING: ['Reading screen', 'Capturing state', 'Detecting elements'],
        PLANNING: ['Building plan', 'Sequencing actions', 'Optimizing path'],
        EXECUTING: ['Clicking element', 'Typing text', 'Opening app'],
        ERROR: ['Recovering from error'],
        IDLE: ['Awaiting input'],
    };

    let timeoutId: NodeJS.Timeout;

    const scheduleNext = () => {
        const delay = 3000 + Math.random() * 5000; // 3-8 seconds
        timeoutId = setTimeout(() => {
            const state = states[Math.floor(Math.random() * states.length)];
            const titleOptions = titles[state];
            const title = titleOptions[Math.floor(Math.random() * titleOptions.length)];

            addActivity({ state, title });
            scheduleNext();
        }, delay);
    };

    scheduleNext();

    return () => clearTimeout(timeoutId);
}

// Format relative time
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

// Format uptime
export function formatUptime(startTime: Date): string {
    const seconds = Math.floor((Date.now() - startTime.getTime()) / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
}
