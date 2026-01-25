/**
 * Skills API Client
 * 
 * Fetches user-scoped skills from backend Firestore.
 */
import type { Skill } from '@/stores/dashboardStore';
import { auth } from '@/lib/firebase';

// Skills API uses local Python microservice (has protected /me/* routes)
// Remote Render server doesn't have these routes, so use localhost
const API_BASE = 'http://localhost:8000';

export interface BackendSkill {
    id: string;
    name: string;
    intent_signature: string;
    description?: string;
    confidence: any; // backend sends string or number
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
    // Derive confidence level from numeric/string confidence
    let confidenceVal = 0.5;
    if (typeof backendSkill.confidence === 'string') {
        confidenceVal = parseFloat(backendSkill.confidence);
    } else if (typeof backendSkill.confidence === 'number') {
        confidenceVal = backendSkill.confidence;
    }

    let confidenceLevel: 'low' | 'medium' | 'high' = 'low';
    if (confidenceVal >= 0.9) {
        confidenceLevel = 'high';
    } else if (confidenceVal >= 0.5) {
        confidenceLevel = 'medium';
    }

    return {
        id: backendSkill.id,
        name: backendSkill.name,
        description: backendSkill.description || backendSkill.intent_signature,
        confidence: confidenceLevel,
        lastExecuted: backendSkill.last_used_at ? new Date(backendSkill.last_used_at) : undefined,
        executionCount: backendSkill.success_count || 0,
    };
}

/**
 * Fetch all skills for the current user from Firestore.
 */
export async function fetchSkills(): Promise<Skill[]> {
    try {
        const token = await getAuthToken();
        // Allow fetch even if no token for dev/local backend

        // Use /me/skills endpoint (protected routes in Python backend)
        const response = await fetch(`${API_BASE}/me/skills`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        });

        if (!response.ok) {
            console.error('[Skills API] Failed to fetch skills:', response.status);
            return [];
        }

        const data = await response.json();
        const skillsList = data.skills || data || [];

        if (Array.isArray(skillsList)) {
            return skillsList.map(toFrontendSkill);
        }
        return [];
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

        const response = await fetch(`${API_BASE}/me/skills`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            },
            body: JSON.stringify(skill),
        });

        if (!response.ok) {
            console.error('[Skills API] Failed to create skill:', response.status);
            return null;
        }

        // Backend returns { status, skill_id, skill_name }
        // We construct a temporary frontend skill to return
        const result = await response.json();

        return {
            id: result.skill_id,
            name: skill.name,
            description: skill.description || '',
            confidence: 'high',
            executionCount: 0
        };
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

        const response = await fetch(`${API_BASE}/me/skills/${skillId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
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

        const response = await fetch(`${API_BASE}/me/skills/${skillId}`, {
            method: 'DELETE',
            headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        });

        return response.ok || response.status === 204;
    } catch (error) {
        console.error('[Skills API] Error deleting skill:', error);
        return false;
    }
}

/**
 * Run a skill by ID.
 */
export async function runSkill(skillId: string): Promise<boolean> {
    try {
        const token = await getAuthToken();

        // Use the correct endpoint: /me/skills/{skill_id}/use
        const response = await fetch(`${API_BASE}/me/skills/${skillId}/use`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            },
        });

        if (!response.ok) {
            console.error('[Skills API] Failed to run skill:', response.status);
            return false;
        }

        return true;
    } catch (error) {
        console.error('[Skills API] Error running skill:', error);
        return false;
    }
}

/**
 * Mark a skill as used (deprecated/legacy - runSkill handles usage count).
 */
export async function useSkill(skillId: string): Promise<Skill | null> {
    return null;
}
