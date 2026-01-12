"""
Agent Decision Engine

Implements intelligent decision-making logic for action selection.
This is the core intelligence layer that decides strategy BEFORE calling Gemini.

Strategy Types:
- REUSE_SKILL: Use an existing skill with high match
- ADAPT_SKILL: Modify an existing skill based on context
- FRESH_REASONING: No matching skill, use Gemini for full reasoning
"""
from typing import Optional
from difflib import SequenceMatcher

from app.db.skills_repo import get_all_skills, get_skills_by_intent
from app.db.agent_sessions_repo import save_activity_event


# Thresholds for decision making
SKILL_MATCH_THRESHOLD = 0.4  # Minimum similarity for skill consideration
HIGH_CONFIDENCE_THRESHOLD = 0.7  # Above this = REUSE_SKILL
MEDIUM_CONFIDENCE_THRESHOLD = 0.5  # Above this = ADAPT_SKILL


def calculate_intent_similarity(user_intent: str, skill_intent: str) -> float:
    """
    Calculate similarity between user intent and skill intent signature.
    
    Uses SequenceMatcher for fuzzy string matching.
    
    Args:
        user_intent: What the user wants to do
        skill_intent: The skill's intent_signature
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not user_intent or not skill_intent:
        return 0.0
    
    # Normalize strings
    user_lower = user_intent.lower().strip()
    skill_lower = skill_intent.lower().strip()
    
    # Direct substring match boost
    if skill_lower in user_lower or user_lower in skill_lower:
        return 0.85
    
    # Fuzzy matching
    return SequenceMatcher(None, user_lower, skill_lower).ratio()


def calculate_skill_score(
    similarity: float, 
    success_count: int,
    last_used_at: Optional[str]
) -> float:
    """
    Calculate overall skill score based on similarity and success history.
    
    Formula: similarity * (1 + log(success_count + 1))
    
    Args:
        similarity: Intent similarity score (0.0-1.0)
        success_count: Number of successful executions
        last_used_at: ISO timestamp of last use (for recency bonus)
        
    Returns:
        Weighted skill score
    """
    import math
    
    # Success bonus (logarithmic to avoid runaway scores)
    success_bonus = 1 + math.log(success_count + 1) * 0.2
    
    # Recency bonus (small boost if recently used)
    recency_bonus = 0.05 if last_used_at else 0.0
    
    return similarity * success_bonus + recency_bonus


def select_best_skill(user_intent: str, available_skills: list) -> Optional[dict]:
    """
    Select the best matching skill for the given intent.
    
    Args:
        user_intent: What the user wants to do
        available_skills: List of skill dictionaries
        
    Returns:
        Best matching skill with scores, or None
    """
    if not available_skills:
        return None
    
    candidates = []
    
    for skill in available_skills:
        similarity = calculate_intent_similarity(
            user_intent, 
            skill.get('intent_signature', '')
        )
        
        # Also check against skill name
        name_similarity = calculate_intent_similarity(
            user_intent,
            skill.get('name', '')
        )
        
        # Use best of intent or name similarity
        best_similarity = max(similarity, name_similarity)
        
        if best_similarity >= SKILL_MATCH_THRESHOLD:
            score = calculate_skill_score(
                best_similarity,
                skill.get('success_count', 0),
                skill.get('last_used_at')
            )
            candidates.append({
                'skill': skill,
                'similarity': best_similarity,
                'score': score
            })
    
    if not candidates:
        return None
    
    # Return highest scoring candidate
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates[0]


def decide_next_action(
    vision_signal: str,
    user_intent: str,
    available_skills: Optional[list] = None,
    last_action: Optional[dict] = None,
    session_id: Optional[str] = None
) -> dict:
    """
    Main decision function. Determines strategy before Gemini is called.
    
    Args:
        vision_signal: Current vision signal (SCREEN_CHANGED, UI_STABLE, etc.)
        user_intent: What the user wants to accomplish
        available_skills: List of available skills (fetched if None)
        last_action: The previous action taken (for context)
        
    Returns:
        Decision dictionary with strategy, confidence, and reasoning
    """
    # Fetch skills if not provided
    if available_skills is None:
        try:
            available_skills = get_all_skills()
        except Exception as e:
            print(f"[DECISION] Failed to fetch skills: {e}")
            available_skills = []
    
    # Default decision: fresh reasoning
    decision = {
        "strategy": "FRESH_REASONING",
        "skill_id": None,
        "skill_name": None,
        "confidence": 0.5,
        "reason": "No matching skill found, using Gemini for fresh reasoning"
    }
    
    # Check vision stability
    if vision_signal == "SCREEN_CHANGED":
        decision["confidence"] = 0.4
        decision["reason"] = "Screen changed significantly, proceeding cautiously with fresh analysis"
        return decision
    
    # If vision is unstable, don't try to reuse skills
    if vision_signal not in ("UI_STABLE", "MINOR_UPDATE"):
        decision["confidence"] = 0.45
        decision["reason"] = f"Unstable vision ({vision_signal}), using fresh reasoning"
        return decision
    
    # Try to find a matching skill
    best_match = select_best_skill(user_intent, available_skills)
    
    if best_match is None:
        return decision
    
    skill = best_match['skill']
    similarity = best_match['similarity']
    score = best_match['score']
    
    # Determine strategy based on confidence
    if similarity >= HIGH_CONFIDENCE_THRESHOLD:
        decision = {
            "strategy": "REUSE_SKILL",
            "skill_id": skill.get('id'),
            "skill_name": skill.get('name'),
            "steps": skill.get('steps', []),
            "confidence": min(0.95, 0.7 + similarity * 0.3),
            "reason": f"High match ({similarity:.0%}) with skill '{skill.get('name')}' (used {skill.get('success_count', 0)}x)"
        }
    elif similarity >= MEDIUM_CONFIDENCE_THRESHOLD:
        decision = {
            "strategy": "ADAPT_SKILL",
            "skill_id": skill.get('id'),
            "skill_name": skill.get('name'),
            "steps": skill.get('steps', []),
            "confidence": 0.5 + similarity * 0.3,
            "reason": f"Partial match ({similarity:.0%}) with '{skill.get('name')}', adapting steps"
        }
    else:
        decision["reason"] = f"Best match '{skill.get('name')}' too weak ({similarity:.0%})"
    
    # Reduce confidence if last action failed
    if last_action and last_action.get('failed'):
        decision["confidence"] *= 0.7
        decision["reason"] += " (reduced due to previous failure)"

    if session_id:
        try:
            save_activity_event(session_id, {
                'state': 'PLANNING',
                'title': f"Strategy: {decision['strategy']}",
                'description': decision['reason']
            })
        except Exception as e:
            print(f"[DECISION] Failed to save activity event: {e}")
    
    return decision


def get_decision_for_gemini(decision: dict) -> str:
    """
    Generate context string for Gemini based on decision.
    
    Args:
        decision: Decision dictionary from decide_next_action
        
    Returns:
        Context string to include in Gemini prompt
    """
    strategy = decision.get('strategy', 'FRESH_REASONING')
    
    if strategy == "REUSE_SKILL":
        steps = decision.get('steps', [])
        steps_desc = "\n".join([
            f"  {s.get('step_index', i+1)}. {s.get('action_type', 'UNKNOWN')}: {s.get('context', '')}"
            for i, s in enumerate(steps)
        ])
        return f"""
[SKILL REUSE - High Confidence Match]
Using existing skill: {decision.get('skill_name')}
Predefined steps:
{steps_desc}

Execute the first applicable step from this skill.
"""
    
    elif strategy == "ADAPT_SKILL":
        return f"""
[SKILL ADAPTATION Required]
Similar skill found: {decision.get('skill_name')}
Confidence: {decision.get('confidence', 0):.0%}

The skill steps may need modification for this specific context.
Use the skill as guidance but adapt to what you see on screen.
"""
    
    else:
        return f"""
[FRESH REASONING Mode]
No matching skill found. Analyze the screen carefully and determine
the best action to accomplish the user's intent.
"""
