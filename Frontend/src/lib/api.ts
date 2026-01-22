// API service layer for backend communication

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export interface LoginRequest {
    email: string;
    password: string;
}

export interface SignupRequest {
    name: string;
    email: string;
    password: string;
}

export interface AuthResponse {
    token: string;
    user: {
        id: number;
        name: string;
        email: string;
    };
}

export interface ApiError {
    message: string;
}

// Get auth token from localStorage
function getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('auth_token');
}

// Set auth token in localStorage
export function setAuthToken(token: string): void {
    if (typeof window !== 'undefined') {
        localStorage.setItem('auth_token', token);
    }
}

// Remove auth token from localStorage
export function removeAuthToken(): void {
    if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token');
    }
}

// Get current user from localStorage
export function getCurrentUser(): AuthResponse['user'] | null {
    if (typeof window === 'undefined') return null;
    const userStr = localStorage.getItem('current_user');
    if (!userStr) return null;
    try {
        return JSON.parse(userStr);
    } catch {
        return null;
    }
}

// Set current user in localStorage
export function setCurrentUser(user: AuthResponse['user']): void {
    if (typeof window !== 'undefined') {
        localStorage.setItem('current_user', JSON.stringify(user));
    }
}

// Remove current user from localStorage
export function clearCurrentUser(): void {
    if (typeof window !== 'undefined') {
        localStorage.removeItem('current_user');
    }
}

// Make API request with authentication
async function apiRequest<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const token = getAuthToken();
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string> || {}),
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        const error: ApiError = await response.json().catch(() => ({
            message: `HTTP error! status: ${response.status}`,
        }));
        throw new Error(error.message || 'An error occurred');
    }

    return response.json();
}

// Auth API
export const authApi = {
    async login(credentials: LoginRequest): Promise<AuthResponse> {
        const response = await apiRequest<AuthResponse>('/auth/login', {
            method: 'POST',
            body: JSON.stringify(credentials),
        });
        setAuthToken(response.token);
        setCurrentUser(response.user);
        return response;
    },

    async signup(data: SignupRequest): Promise<AuthResponse> {
        const response = await apiRequest<AuthResponse>('/auth/signup', {
            method: 'POST',
            body: JSON.stringify(data),
        });
        setAuthToken(response.token);
        setCurrentUser(response.user);
        return response;
    },

    async getCurrentUser(): Promise<AuthResponse['user']> {
        return apiRequest<AuthResponse['user']>('/auth/me');
    },

    logout(): void {
        removeAuthToken();
        clearCurrentUser();
    },
};

// Check if user is authenticated
export function isAuthenticated(): boolean {
    return getAuthToken() !== null;
}

// Dashboard API
export const dashboardApi = {
    async getSkills() {
        return apiRequest<any[]>('/dashboard/skills');
    },

    async getActivities() {
        return apiRequest<any[]>('/dashboard/activities');
    },

    async getMetrics() {
        return apiRequest<any>('/dashboard/metrics');
    },

    async getStats() {
        return apiRequest<any>('/dashboard/stats');
    },
};

