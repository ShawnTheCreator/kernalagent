"""
Pydantic schemas for Kernal Agent AI Brain.
Defines the structured output format for Gemini responses.
"""
from pydantic import BaseModel, Field
from typing import Literal


class KernalAction(BaseModel):
    """
    The strict structure of an action plan returned by the AI.
    Used for structured JSON output from Gemini.
    """
    explanation: str = Field(
        description="A short reasoning of why this action was chosen."
    )
    action_type: Literal["CLICK", "TYPE", "SCROLL", "WAIT", "DONE"] = Field(
        description="The type of OS action to perform."
    )
    coordinate_label: int | None = Field(
        default=None,
        description="The ID number of the detected element to click (from Set-of-Mark)."
    )
    text_payload: str | None = Field(
        default=None,
        description="Text to type (if action_type is TYPE)."
    )


class IntentUpdate(BaseModel):
    """Message format for intent updates from the client."""
    type: Literal["intent_update"]
    payload: str


class FrameData(BaseModel):
    """Message format for frame data from the client."""
    type: Literal["frame"]
    image: str  # Base64 encoded image
