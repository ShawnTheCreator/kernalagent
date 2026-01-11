"""
Pydantic schemas for Kernal Agent AI Brain.
Defines the structured output format for Gemini responses.
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional


class KernalAction(BaseModel):
    """
    The strict structure of an action plan returned by the AI.
    Used for structured JSON output from Gemini.
    
    Every action includes:
    - explanation: Why this action was chosen
    - action_type: What to do (CLICK, TYPE, etc.)
    - confidence: How confident the agent is (0.0-1.0)
    - strategy: Decision strategy used (REUSE_SKILL, ADAPT_SKILL, FRESH_REASONING)
    """
    explanation: str = Field(
        description="A short reasoning of why this action was chosen."
    )
    action_type: Literal["CLICK", "TYPE", "SCROLL", "WAIT", "DONE"] = Field(
        description="The type of OS action to perform."
    )
    coordinate_label: Optional[int] = Field(
        default=None,
        description="The ID number of the detected element to click (from Set-of-Mark)."
    )
    text_payload: Optional[str] = Field(
        default=None,
        description="Text to type (if action_type is TYPE)."
    )
    confidence: float = Field(
        default=0.5,
        description="Confidence level for this action (0.0 to 1.0)."
    )
    strategy: Literal["REUSE_SKILL", "ADAPT_SKILL", "FRESH_REASONING"] = Field(
        default="FRESH_REASONING",
        description="The decision strategy used to select this action."
    )
    skill_id: Optional[str] = Field(
        default=None,
        description="ID of the skill being used (if strategy is REUSE_SKILL or ADAPT_SKILL)."
    )


class IntentUpdate(BaseModel):
    """Message format for intent updates from the client."""
    type: Literal["intent_update"]
    payload: str


class FrameData(BaseModel):
    """Message format for frame data from the client."""
    type: Literal["frame"]
    image: str  # Base64 encoded image


class VisionSignal(BaseModel):
    """Vision signal detected from screenshot comparison."""
    signal_type: Literal["SCREEN_CHANGED", "LAYOUT_CHANGE", "MINOR_UPDATE", "UI_STABLE"]
    confidence: float = Field(default=0.8, description="Confidence of signal detection")
