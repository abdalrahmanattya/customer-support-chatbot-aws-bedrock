"""Data models package for Customer Support Chatbot."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SupportIntent(str, Enum):
    """Guaranteed valid category enums for customer inquiries."""
    BUG_REPORT = "BUG_REPORT"
    PLATFORM_QUESTION = "PLATFORM_QUESTION"
    OTHER_REQUEST = "OTHER_REQUEST"


class IntentClassificationResult(BaseModel):
    """Guaranteed structured output schema from the Intent Classifier."""
    intent: SupportIntent = Field(description="The classified customer intent category.")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0.")
    reasoning: str = Field(description="Brief explanation justifying the chosen classification.")
    detected_entities: dict[str, Any] = Field(default_factory=dict, description="Extracted entities such as orderNumber, errorDetails, browser, etc.")
