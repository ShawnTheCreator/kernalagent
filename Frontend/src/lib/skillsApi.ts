/**
 * Skills API Client
 * 
 * Fetches user-scoped skills from backend Firestore.
 * Uses authenticated endpoints at /me/skills.
 */
import type { Skill } from '@/stores/dashboardStore';
import { auth } from '@/lib/firebase';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export interface BackendSkill {
    id: string;
    name: string;
    intent_signature: string;
    description?: string;
    confidence: number;
    success_count: number;
    last_used_at: string | null;
    created_at?: string;
}

export interface CreateSkillRequest {
    name: string;
    intent_signature: string;
    description?: string;
    steps?: any[];
    confidence?: number;
}

export interface UpdateSkillRequest {
    name?: string;
    intent_signature?: string;
    description?: string;
    confidence?: number;
}

/**
 * Get Firebase Auth token for authenticated requests.
 */
async function getAuthToken(): Promise<string | null> {
    const user = auth.currentUser;
    if (!user) return null;
    return user.getIdToken();
}

/**
 * Convert backend skill to frontend Skill type.
 */
function toFrontendSkill(backendSkill: BackendSkill): Skill {
    // Derive confidence level from numeric confidence
    let confidenceLevel: 'low' | 'medium' | 'high' = 'low';
    if (backendSkill.confidence >= 0.7) {
        confidenceLevel = 'high';
    } else if (backendSkill.confidence >= 0.4) {
        confidenceLevel = 'medium';
    }

    return {
        id: backendSkill.id,
        name: backendSkill.name,
        description: backendSkill.description || backendSkill.intent_signature,
        confidence: confidenceLevel,
        lastExecuted: backendSkill.last_used_at ? new Date(backendSkill.last_used_at) : undefined,
        executionCount: backendSkill.success_count,
    };
}

/**
 * Fetch all skills for the current user from Firestore.
 */
export async function fetchSkills(): Promise<Skill[]> {
    try {
        const token = await getAuthToken();
        if (!token) {
            console.warn('[Skills API] No auth token, user not logged in');
            return [];
        }

        const response = await fetch(`${API_BASE}/me/skills`, {
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        });

        if (!response.ok) {
            console.error('[Skills API] Failed to fetch skills:', response.status);
            return [];
        }

        const data: BackendSkill[] = await response.json();
        return data.map(toFrontendSkill);
    } catch (error) {
        console.error('[Skills API] Error fetching skills:', error);
        return [];
    }
}

/**
 * Create a new skill for the current user.
 */
export async function createSkill(skill: CreateSkillRequest): Promise<Skill | null> {
    try {
        const token = await getAuthToken();
        if (!token) return null;

        const response = await fetch(`${API_BASE}/me/skills`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(skill),
        });

        if (!response.ok) {
            console.error('[Skills API] Failed to create skill:', response.status);
            return null;
        }

        const data: BackendSkill = await response.json();
        return toFrontendSkill(data);
    } catch (error) {
        console.error('[Skills API] Error creating skill:', error);
        return null;
    }
}

/**
 * Update an existing skill.
 */
export async function updateSkill(skillId: string, updates: UpdateSkillRequest): Promise<Skill | null> {
    try {
        const token = await getAuthToken();
        if (!token) return null;

        const response = await fetch(`${API_BASE}/me/skills/${skillId}`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updates),
        });

        if (!response.ok) {
            console.error('[Skills API] Failed to update skill:', response.status);
            return null;
        }

        const data: BackendSkill = await response.json();
        return toFrontendSkill(data);
    } catch (error) {
        console.error('[Skills API] Error updating skill:', error);
        return null;
    }
}

/**
 * Delete a skill.
 */
export async function deleteSkill(skillId: string): Promise<boolean> {
    try {
        const token = await getAuthToken();
        if (!token) return false;

        const response = await fetch(`${API_BASE}/me/skills/${skillId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        });

        return response.ok || response.status === 204;
    } catch (error) {
        console.error('[Skills API] Error deleting skill:', error);
        return false;
    }
}

/**
 * Mark a skill as used (increments success_count).
 */
export async function useSkill(skillId: string): Promise<Skill | null> {
    try {
        const token = await getAuthToken();
        if (!token) return null;

        const response = await fetch(`${API_BASE}/me/skills/${skillId}/use`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        });

        if (!response.ok) {
            console.error('[Skills API] Failed to use skill:', response.status);
            return null;
        }

        const data: BackendSkill = await response.json();
        return toFrontendSkill(data);
    } catch (error) {
        console.error('[Skills API] Error using skill:', error);
        return null;
    }
}
