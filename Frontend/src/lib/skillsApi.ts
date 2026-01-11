/**
 * Skills API Client
 * 
 * Fetches skills from backend SQLite and triggers skill execution.
 */
import type { Skill } from '@/stores/dashboardStore';

// Toggle: Set to true to use local backend (localhost:8000), false for Render
const USE_LOCAL_API = false;

const LOCAL_API = 'http://localhost:8000';
const RENDER_API = 'https://kernalagent.onrender.com';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || (USE_LOCAL_API ? LOCAL_API : RENDER_API);

export interface BackendSkill {
    id: string;
    name: string;
    intent_signature: string;
    steps: BackendSkillStep[];
    created_at: string;
    last_used_at: string | null;
    success_count: number;
}

export interface BackendSkillStep {
    step_index: number;
    action_type: string;
    context: string;
    vision_expectation: string;
}

export interface RunSkillResponse {
    status: string;
    skill_id: string;
    skill_name: string;
}

/**
 * Convert backend skill to frontend Skill type.
 */
function toFrontendSkill(backendSkill: BackendSkill): Skill {
    // Derive confidence from success_count
    let confidence: 'low' | 'medium' | 'high' = 'low';
    if (backendSkill.success_count >= 5) {
        confidence = 'high';
    } else if (backendSkill.success_count >= 2) {
        confidence = 'medium';
    }

    return {
        id: backendSkill.id,
        name: backendSkill.name,
        description: backendSkill.intent_signature,
        confidence,
        lastExecuted: backendSkill.last_used_at ? new Date(backendSkill.last_used_at) : undefined,
        executionCount: backendSkill.success_count,
    };
}

/**
 * Fetch all skills from backend.
 */
export async function fetchSkills(): Promise<Skill[]> {
    try {
        const response = await fetch(`${API_BASE}/api/skills`);
        if (!response.ok) {
            console.error('[Skills API] Failed to fetch skills:', response.statusText);
            return [];
        }
        const data = await response.json();
        return data.skills.map(toFrontendSkill);
    } catch (error) {
        console.error('[Skills API] Error fetching skills:', error);
        return [];
    }
}

/**
 * Run a skill on the desktop agent.
 */
export async function runSkill(skillId: string): Promise<RunSkillResponse | null> {
    try {
        const response = await fetch(`${API_BASE}/api/skills/run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ skill_id: skillId }),
        });

        if (!response.ok) {
            console.error('[Skills API] Failed to run skill:', response.statusText);
            return null;
        }

        return await response.json();
    } catch (error) {
        console.error('[Skills API] Error running skill:', error);
        return null;
    }
}
