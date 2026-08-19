"""Structured Output Intent Classifier for Customer Support Chatbot."""

import logging
from typing import Any

from src.agent.models.intent import IntentClassificationResult, SupportIntent

logger = logging.getLogger(__name__)

CLASSIFIER_TOOL_SPEC: dict[str, Any] = {
    "toolSpec": {
        "name": "classify_intent",
        "description": "Classify the customer's message into exactly one of three valid intent categories.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": ["BUG_REPORT", "PLATFORM_QUESTION", "OTHER_REQUEST"],
                        "description": (
                            "Categorical classification: "
                            "BUG_REPORT (software defect, crash, glitch, broken button), "
                            "PLATFORM_QUESTION (orders, shipping, returns, refunds, payments, account policies), "
                            "OTHER_REQUEST (unrelated topics, general chitchat, non-store questions)."
                        ),
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Confidence score between 0.0 and 1.0.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation justifying the classification.",
                    },
                    "detected_entities": {
                        "type": "object",
                        "description": "Key extracted entities like device, browser, order_id, product_name.",
                    },
                },
                "required": ["intent", "confidence", "reasoning"],
            }
        }
    }
}


CLASSIFIER_SYSTEM_PROMPT = """You are an accurate intent classifier for an online store customer support system.
Analyze the user's message and call the `classify_intent` tool with the appropriate intent, confidence score, and extracted entities.
Categories:
- BUG_REPORT: Technical malfunctions, crash reports, checkout errors, 500 errors, broken buttons, UI defects.
- PLATFORM_QUESTION: Official store policies regarding returns, refunds, order tracking, shipping, payment methods, accounts, passwords.
- OTHER_REQUEST: Queries outside online shop operations, chit-chat, cooking recipes, mechanics, general knowledge.
"""


class IntentClassifier:
    """
    Deterministic intent classifier using Bedrock tool forcing and Pydantic validation.
    Guarantees that all classification outputs strictly conform to SupportIntent enums.
    """

    def __init__(
        self,
        model_id: str = "amazon.nova-pro-v1:0",
        bedrock_client: Any = None,
        mock_mode: bool = False
    ):
        self.model_id = model_id
        self.bedrock_client = bedrock_client
        self.mock_mode = mock_mode

    def classify(self, message: str) -> IntentClassificationResult:
        """
        Classify a message and return a guaranteed IntentClassificationResult instance.
        """
        clean_text = message.strip()
        if not clean_text:
            return IntentClassificationResult(
                intent=SupportIntent.OTHER_REQUEST,
                confidence=0.5,
                reasoning="Empty message provided."
            )

        if self.mock_mode or not self.bedrock_client:
            return self._mock_classify(clean_text)

        # Live Bedrock Structured Classification using Tool Forcing
        try:
            response = self.bedrock_client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": clean_text}]}],
                system=[{"text": CLASSIFIER_SYSTEM_PROMPT}],
                toolConfig={
                    "tools": [CLASSIFIER_TOOL_SPEC],
                    "toolChoice": {"tool": {"name": "classify_intent"}},
                },
                inferenceConfig={"temperature": 0.0, "maxTokens": 256}
            )

            output_blocks = response.get("output", {}).get("message", {}).get("content", [])
            for block in output_blocks:
                if "toolUse" in block and block["toolUse"].get("name") == "classify_intent":
                    raw_input = block["toolUse"].get("input", {})
                    return IntentClassificationResult(**raw_input)

            # Fallback if model did not trigger tool use
            return self._mock_classify(clean_text)
        except Exception as exc:
            logger.warning("Bedrock structured classification failed (%s), using local rules", exc)
            return self._mock_classify(clean_text)

    def _mock_classify(self, text: str) -> IntentClassificationResult:
        """Deterministic heuristic classifier for offline testing."""
        t = text.lower()

        # 1. Check for Bug Report Intent
        bug_signals = ["bug", "error", "broken", "crash", "glitch", "doesn't work", "fails", "problem", "spinner", "500"]
        if any(sig in t for sig in bug_signals):
            entities = {}
            if "chrome" in t:
                entities["browser"] = "Chrome"
            elif "safari" in t:
                entities["browser"] = "Safari"
            if "macos" in t or "mac" in t:
                entities["os"] = "macOS"
            return IntentClassificationResult(
                intent=SupportIntent.BUG_REPORT,
                confidence=0.95,
                reasoning="Message contains technical malfunction or error report keywords.",
                detected_entities=entities
            )

        # 2. Check for Platform Question Intent
        faq_signals = [
            "return", "refund", "exchange", "ship", "delivery", "track", "tracking",
            "order", "pay", "payment", "card", "account", "password", "hours", "contact"
        ]
        if any(sig in t for sig in faq_signals):
            return IntentClassificationResult(
                intent=SupportIntent.PLATFORM_QUESTION,
                confidence=0.92,
                reasoning="Message inquires about verified store policies or account management."
            )

        # 3. Default to Other Request
        return IntentClassificationResult(
            intent=SupportIntent.OTHER_REQUEST,
            confidence=0.85,
            reasoning="Query is outside the scope of online shop support operations."
        )
