"""Unit tests for Structured Output Intent Classifier."""

import pytest
from pydantic import ValidationError

from src.agent.classifier import CLASSIFIER_TOOL_SPEC, IntentClassifier
from src.agent.models.intent import IntentClassificationResult, SupportIntent


def test_support_intent_enums():
    """Verify enum members exist and match expected string values."""
    assert SupportIntent.BUG_REPORT.value == "BUG_REPORT"
    assert SupportIntent.PLATFORM_QUESTION.value == "PLATFORM_QUESTION"
    assert SupportIntent.OTHER_REQUEST.value == "OTHER_REQUEST"


def test_intent_classification_result_validation():
    """Verify Pydantic model validation on classification result."""
    valid_data = {
        "intent": "BUG_REPORT",
        "confidence": 0.95,
        "reasoning": "Checkout failed with a spinner on Chrome.",
        "detected_entities": {"browser": "Chrome", "os": "macOS"},
    }
    result = IntentClassificationResult(**valid_data)
    assert result.intent == SupportIntent.BUG_REPORT
    assert result.confidence == 0.95
    assert result.detected_entities["browser"] == "Chrome"

    # Test invalid intent rejection
    with pytest.raises(ValidationError):
        IntentClassificationResult(
            intent="INVALID_CATEGORY",
            confidence=0.5,
            reasoning="Invalid intent should fail validation."
        )


def test_classifier_tool_spec_schema():
    """Verify tool specification meets Bedrock Converse API format."""
    tool_spec = CLASSIFIER_TOOL_SPEC["toolSpec"]
    assert tool_spec["name"] == "classify_intent"
    props = tool_spec["inputSchema"]["json"]["properties"]
    assert "intent" in props
    assert props["intent"]["enum"] == ["BUG_REPORT", "PLATFORM_QUESTION", "OTHER_REQUEST"]
    assert "confidence" in props
    assert "reasoning" in props


def test_classifier_mock_predictions():
    """Verify deterministic mock classification across diverse inputs."""
    classifier = IntentClassifier(mock_mode=True)

    # Bug report queries
    r1 = classifier.classify("The checkout page crashes on Chrome when I click Place Order.")
    assert r1.intent == SupportIntent.BUG_REPORT
    assert r1.confidence >= 0.9
    assert r1.detected_entities.get("browser") == "Chrome"

    # Platform question queries
    r2 = classifier.classify("What is your return policy and how long do refunds take?")
    assert r2.intent == SupportIntent.PLATFORM_QUESTION
    assert r2.confidence >= 0.9

    # Other request queries
    r3 = classifier.classify("What is the recipe for baking sourdough bread?")
    assert r3.intent == SupportIntent.OTHER_REQUEST
    assert r3.confidence >= 0.8

    # Empty string
    r4 = classifier.classify("")
    assert isinstance(r4, IntentClassificationResult)
    assert r4.intent == SupportIntent.OTHER_REQUEST
