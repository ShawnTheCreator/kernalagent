"""
Agent Decision Engine (v2 - Improved Intelligence)

Implements intelligent decision-making logic for action selection.
This is the core intelligence layer that decides strategy BEFORE calling Gemini.

v2 Changes:
- Added action verb awareness for better intent matching
- Lowered thresholds to trigger skill reuse more often
- Relaxed vision gating for expected layout changes
- Use confidence to ADAPT, not BLOCK

Strategy Types:
- REUSE_SKILL: Use an existing skill with good match
- ADAPT_SKILL: Modify an existing skill based on context
- FRESH_REASONING: No matching skill, use Gemini for full reasoning
"""
from typing import Optional
from difflib import SequenceMatcher

from app.db.skills_repo import get_all_skills, get_skills_by_intent


# ============================================================================
# THRESHOLDS (v2 - More aggressive skill reuse)
# ============================================================================
SKILL_MATCH_THRESHOLD = 0.30  # Lowered from 0.4 - consider skills earlier
HIGH_CONFIDENCE_THRESHOLD = 0.50  # Lowered from 0.7 - reuse more often
MEDIUM_CONFIDENCE_THRESHOLD = 0.35  # Lowered from 0.5 - adapt more often

# Action verb boost percentage
ACTION_VERB_BOOST = 0.20  # +20% boost when action verbs match


# ============================================================================
# ACTION VERB MAPPINGS (Semantic awareness)
# ============================================================================
ACTION_VERBS = {
    "open": ["open", "launch", "start", "run", "execute", "begin"],
    "click": ["click", "press", "tap", "select", "choose", "hit"],
    "type": ["type", "enter", "write", "input", "fill", "insert"],
    "scroll": ["scroll", "page down", "page up", "move down", "move up", "navigate"],
    "analyze": ["analyze", "inspect", "scan", "examine", "look", "check", "view"],
    "close": ["close", "exit", "quit", "end", "terminate", "stop"],
    "search": ["search", "find", "look for", "locate", "seek"],
    "copy": ["copy", "duplicate", "clone"],
    "paste": ["paste", "insert"],
    "save": ["save", "store", "export", "download"],
}

# Vision signals that are EXPECTED for certain action types
EXPECTED_VISION_FOR_ACTION = {
    "scroll": ["LAYOUT_CHANGE", "MINOR_UPDATE", "UI_STABLE"],
    "open": ["SCREEN_CHANGED", "LAYOUT_CHANGE"],
    "click": ["SCREEN_CHANGED", "LAYOUT_CHANGE", "MINOR_UPDATE"],
    "navigate": ["SCREEN_CHANGED", "LAYOUT_CHANGE"],
    "menu": ["LAYOUT_CHANGE", "MINOR_UPDATE"],
}


def get_action_verb(text: str) -> Optional[str]:
    """
    Extract the primary action verb from text.
    
    Args:
        text: User intent or skill description
        
    Returns:
        Matched action verb category or None
    """
    text_lower = text.lower()
    
    for category, verbs in ACTION_VERBS.items():
        for verb in verbs:
            if verb in text_lower:
                return category
    
    return None


def calculate_intent_similarity(user_intent: str, skill_intent: str) -> float:
    """
    Calculate similarity between user intent and skill intent signature.
    
    v2: Added action verb awareness for semantic matching.
    
    Args:
        user_intent: What the user wants to do
        skill_intent: The skill's intent_signature
        
    Returns:
        Similarity score between 0.0 and 1.0 (can exceed 1.0 with boosts, clamped)
    """
    if not user_intent or not skill_intent:
        return 0.0
    
    # Normalize strings
    user_lower = user_intent.lower().strip()
    skill_lower = skill_intent.lower().strip()
    
    # Base similarity using fuzzy matching
    base_similarity = SequenceMatcher(None, user_lower, skill_lower).ratio()
    
    # Direct substring match boost (strong signal)
    if skill_lower in user_lower or user_lower in skill_lower:
        base_similarity = max(base_similarity, 0.80)
    
    # ACTION VERB BOOST (v2) - semantic matching
    user_verb = get_action_verb(user_lower)
    skill_verb = get_action_verb(skill_lower)
    
    if user_verb and skill_verb and user_verb == skill_verb:
        # Same action verb category = significant boost
        base_similarity += ACTION_VERB_BOOST
    
    # Word overlap bonus (for partial matches)
    user_words = set(user_lower.split())
    skill_words = set(skill_lower.split())
    common_words = user_words & skill_words
    
    if len(common_words) >= 2:
        base_similarity += 0.10  # Bonus for shared keywords
    elif len(common_words) >= 1:
        base_similarity += 0.05
    
    # Clamp to reasonable range
    return min(1.0, base_similarity)


def calculate_skill_score(
    similarity: float, 
    success_count: int,
    last_used_at: Optional[str]
) -> float:
    """
    Calculate overall skill score based on similarity and success history.
    
    v2 Formula: similarity * (1 + success_count * 0.15)
    - More weight to success_count for proven skills
    
    Args:
        similarity: Intent similarity score (0.0-1.0)
        success_count: Number of successful executions
        last_used_at: ISO timestamp of last use (for recency bonus)
        
    Returns:
        Weighted skill score
    """
    # Success bonus (linear, stronger than before)
    # A skill used 5x gets similarity * 1.75
    success_bonus = 1 + success_count * 0.15
    
    # Recency bonus (moderate boost if recently used)
    recency_bonus = 0.08 if last_used_at else 0.0
    
    return similarity * success_bonus + recency_bonus


def is_vision_expected_for_intent(vision_signal: str, user_intent: str) -> bool:
    """
    Check if the vision signal is expected for the type of action.
    
    v2: LAYOUT_CHANGE is expected for scroll/navigation/menu actions.
    
    Args:
        vision_signal: Current vision signal
        user_intent: User's intent
        
    Returns:
        True if this signal is reasonable for the intent
    """
    user_lower = user_intent.lower()
    
    for action_type, expected_signals in EXPECTED_VISION_FOR_ACTION.items():
        if action_type in user_lower:
            if vision_signal in expected_signals:
                return True
    
    # UI_STABLE and MINOR_UPDATE are always acceptable
    if vision_signal in ("UI_STABLE", "MINOR_UPDATE"):
        return True
    
    return False


def select_best_skill(user_intent: str, available_skills: list) -> Optional[dict]:
    """
    Select the best matching skill for the given intent.
    
    v2: Lower threshold, prefer skills with success history.
    
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
        # Check similarity against intent signature
        similarity = calculate_intent_similarity(
            user_intent, 
            skill.get('intent_signature', '')
        )
        
        # Also check against skill name (often more descriptive)
        name_similarity = calculate_intent_similarity(
            user_intent,
            skill.get('name', '')
        )
        
        # Use best of intent or name similarity
        best_similarity = max(similarity, name_similarity)
        
        # v2: Lower threshold AND prefer proven skills
        success_count = skill.get('success_count', 0)
        
        # If skill has been used successfully, lower the bar
        effective_threshold = SKILL_MATCH_THRESHOLD
        if success_count > 0:
            effective_threshold = max(0.25, SKILL_MATCH_THRESHOLD - 0.05)
        if success_count >= 3:
            effective_threshold = max(0.20, SKILL_MATCH_THRESHOLD - 0.10)
        
        if best_similarity >= effective_threshold:
            score = calculate_skill_score(
                best_similarity,
                success_count,
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
    last_action: Optional[dict] = None
) -> dict:
    """
    Main decision function. Determines strategy before Gemini is called.
    
    v2 Changes:
    - Relaxed vision gating (LAYOUT_CHANGE can still use skills)
    - Lower thresholds for skill reuse
    - Use confidence to ADAPT, not BLOCK
    
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
    
    # v2: Check if vision signal is expected for this intent
    vision_expected = is_vision_expected_for_intent(vision_signal, user_intent)
    
    # Only block on truly unexpected SCREEN_CHANGED with repeated failures
    if vision_signal == "SCREEN_CHANGED" and not vision_expected:
        if last_action and last_action.get('failed'):
            decision["confidence"] = 0.35
            decision["reason"] = "Unexpected screen change after failure, proceeding cautiously"
            return decision
        else:
            # First unexpected change - still try to find a skill
            decision["confidence"] = 0.45
            # Don't return early - try to find a matching skill anyway
    
    # v2: LAYOUT_CHANGE is NOT a blocker - it's often expected
    # Only warn, don't block
    if vision_signal == "LAYOUT_CHANGE" and not vision_expected:
        decision["confidence"] = 0.50  # Slight caution, but not blocking
    
    # Try to find a matching skill
    best_match = select_best_skill(user_intent, available_skills)
    
    if best_match is None:
        return decision
    
    skill = best_match['skill']
    similarity = best_match['similarity']
    score = best_match['score']
    success_count = skill.get('success_count', 0)
    
    # v2: Determine strategy with lower thresholds
    # Also consider success_count when deciding
    
    # Boost similarity conceptually if skill is proven
    effective_similarity = similarity
    if success_count >= 3:
        effective_similarity = min(1.0, similarity + 0.10)  # Proven skill boost
    elif success_count >= 1:
        effective_similarity = min(1.0, similarity + 0.05)
    
    if effective_similarity >= HIGH_CONFIDENCE_THRESHOLD:
        # REUSE_SKILL: High confidence match
        decision = {
            "strategy": "REUSE_SKILL",
            "skill_id": skill.get('id'),
            "skill_name": skill.get('name'),
            "steps": skill.get('steps', []),
            "confidence": min(0.95, 0.65 + effective_similarity * 0.3),
            "reason": f"Good match ({similarity:.0%}) with '{skill.get('name')}' (used {success_count}x successfully)"
        }
    elif effective_similarity >= MEDIUM_CONFIDENCE_THRESHOLD:
        # v2 CHANGE: Low confidence + skill = ADAPT_SKILL, not FRESH_REASONING
        decision = {
            "strategy": "ADAPT_SKILL",
            "skill_id": skill.get('id'),
            "skill_name": skill.get('name'),
            "steps": skill.get('steps', []),
            "confidence": 0.45 + effective_similarity * 0.35,
            "reason": f"Partial match ({similarity:.0%}) with '{skill.get('name')}', adapting for context"
        }
    else:
        # Still found a skill, but too weak - mention it
        decision["reason"] = f"Best match '{skill.get('name')}' similarity too low ({similarity:.0%})"
    
    # Reduce confidence if last action failed (but don't switch strategy)
    if last_action and last_action.get('failed'):
        decision["confidence"] *= 0.75
        decision["reason"] += " (caution: previous action failed)"
    
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
[SKILL REUSE - Matched Skill]
Using existing skill: {decision.get('skill_name')}
Confidence: {decision.get('confidence', 0):.0%}
Predefined steps:
{steps_desc}

Execute the first applicable step from this skill.
"""
    
    elif strategy == "ADAPT_SKILL":
        steps = decision.get('steps', [])
        steps_desc = "\n".join([
            f"  {s.get('step_index', i+1)}. {s.get('action_type', 'UNKNOWN')}: {s.get('context', '')}"
            for i, s in enumerate(steps)
        ])
        return f"""
[SKILL ADAPTATION Mode]
Similar skill found: {decision.get('skill_name')}
Confidence: {decision.get('confidence', 0):.0%}
Reference steps:
{steps_desc}

Use these steps as guidance, but adapt to what you see on screen.
The context may differ slightly from when this skill was learned.
"""
    
    else:
        return f"""
[FRESH REASONING Mode]
{decision.get('reason', 'No matching skill found.')}

Analyze the screen carefully and determine the best action 
to accomplish the user's intent.
"""
