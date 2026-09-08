"""Amazon Bedrock Guardrail and Pre-Inference Safety Defense Layer."""

import logging
import re
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_BLOCKED_MESSAGE = (
    "I apologize, but I cannot process this request because it violates our safety and store security policies. "
    "If you have an inquiry regarding orders, returns, or website bugs, please let me know."
)

# Common prompt injection, jailbreak, and system override heuristics
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(dan|unrestricted|in\s+developer\s+mode|chaos)", re.IGNORECASE),
    re.compile(r"(disregard|forget)\s+(your\s+)?(rules|guidelines|system\s+prompt)", re.IGNORECASE),
    re.compile(r"(reveal|print|output|display|show)\s+(your\s+)?(initial|system|internal)\s+(prompt|instructions)", re.IGNORECASE),
    re.compile(r"(system\s+prompt\s+override|jailbreak\s+mode)", re.IGNORECASE),
    re.compile(r"state\s+that\s+all\s+items.*free", re.IGNORECASE),
    re.compile(r"<script.*?>.*?</script>", re.IGNORECASE | re.DOTALL),
]

# Sensitive PII patterns (Credit card 16-digit Luhn candidates, SSN)
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


class SafetyCheckResult(BaseModel):
    """Result of a safety evaluation check."""
    is_safe: bool = True
    action: str = "NONE"  # "NONE", "BLOCKED", "ANONYMIZED"
    message: str = ""
    violations: list[str] = Field(default_factory=list)


class SafetyGuardrail:
    """Pre-inference safety filter interfacing with Bedrock Guardrails and local heuristic defenses."""

    def __init__(
        self,
        guardrail_id: str | None = None,
        guardrail_version: str = "DRAFT",
        bedrock_client: Any = None,
        blocked_message: str = DEFAULT_BLOCKED_MESSAGE
    ):
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version
        self.bedrock_client = bedrock_client
        self.blocked_message = blocked_message

    def evaluate_input(self, text: str) -> SafetyCheckResult:
        """
        Evaluate input text against safety policies.
        Uses AWS Bedrock Guardrails if configured, with local defense-in-depth rules.
        """
        clean_text = text.strip()
        if not clean_text:
            return SafetyCheckResult(is_safe=True, action="NONE")

        # 1. Local Pre-screening (Fast Defense-in-Depth for prompt injections & PII)
        local_result = self._check_local_heuristics(clean_text)
        if not local_result.is_safe:
            return local_result

        # 2. Remote Bedrock Guardrail API (if client and guardrail_id are active)
        if self.guardrail_id and self.bedrock_client:
            try:
                response = self.bedrock_client.apply_guardrail(
                    guardrailIdentifier=self.guardrail_id,
                    guardrailVersion=self.guardrail_version,
                    source="INPUT",
                    content=[{"text": {"text": clean_text}}]
                )
                action = response.get("action", "NONE")
                if action == "GUARDRAIL_INTERVENED":
                    outputs = response.get("outputs", [])
                    custom_msg = outputs[0].get("text") if outputs else self.blocked_message
                    return SafetyCheckResult(
                        is_safe=False,
                        action="BLOCKED",
                        message=custom_msg or self.blocked_message,
                        violations=["bedrock_guardrail_policy_violation"]
                    )
            except Exception as exc:
                logger.warning("Bedrock apply_guardrail API error (%s), using local safety checks", exc)

        return SafetyCheckResult(is_safe=True, action="NONE")

    def _check_local_heuristics(self, text: str) -> SafetyCheckResult:
        """Analyze text for prompt injections, system prompt leak requests, and raw PII."""
        violations = []

        # Check for prompt injection / jailbreaks
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                violations.append("prompt_attack")
                break

        # Check for exposed raw credit card numbers
        if CREDIT_CARD_PATTERN.search(text.replace("-", "").replace(" ", "")):
            # Check if digits sequence is 13-16 digits
            digits = re.sub(r"\D", "", text)
            if 13 <= len(digits) <= 19 and digits not in ("1234567890123456",):
                violations.append("credit_card_pii")

        # Check for raw SSN
        if SSN_PATTERN.search(text):
            violations.append("ssn_pii")

        if violations:
            logger.info("Safety guardrail blocked input due to violations: %s", violations)
            return SafetyCheckResult(
                is_safe=False,
                action="BLOCKED",
                message=self.blocked_message,
                violations=violations
            )

        return SafetyCheckResult(is_safe=True, action="NONE")
