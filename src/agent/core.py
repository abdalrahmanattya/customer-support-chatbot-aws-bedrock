"""Main Amazon Bedrock AgentCore Assistant orchestrator."""

import logging
from typing import Any

import boto3
from pydantic import BaseModel, Field

from src.agent.config import AgentConfig
from src.agent.guardrails.safety_filter import SafetyGuardrail
from src.agent.prompts.system_prompt import get_system_prompt
from src.agent.rag.retriever import KnowledgeBaseRetriever
from src.agent.session import SessionMemory
from src.agent.tools.bug_report import BUG_REPORT_TOOL_SPEC, execute_bug_report_tool

logger = logging.getLogger(__name__)


class ToolCallRecord(BaseModel):
    """Metadata tracking a single tool call execution."""
    tool_use_id: str
    tool_name: str
    tool_input: dict[str, Any]
    tool_result: dict[str, Any]


class AgentResponse(BaseModel):
    """Standardized response from the Customer Support Agent."""
    text: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    stop_reason: str = "end_turn"
    session_id: str = ""


class CustomerSupportAgent:
    """AgentCore Orchestration Engine for Customer Support Chatbot."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        boto_session: boto3.Session | None = None
    ):
        self.config = config or AgentConfig()
        self.boto_session = boto_session or boto3.Session(region_name=self.config.region_name)
        self.system_prompt = [{"text": get_system_prompt()}]
        self.tool_config = {"tools": [BUG_REPORT_TOOL_SPEC]}

        if not self.config.mock_mode:
            try:
                self.bedrock_client = self.boto_session.client(
                    "bedrock-runtime",
                    region_name=self.config.region_name
                )
            except Exception as exc:
                logger.warning("Could not initialize Bedrock client (%s), falling back to mock mode", exc)
                self.config.mock_mode = True
                self.bedrock_client = None
        else:
            self.bedrock_client = None

        self.guardrail = SafetyGuardrail(
            guardrail_id=self.config.guardrail_id,
            guardrail_version=self.config.guardrail_version,
            bedrock_client=self.bedrock_client
        )
        self.retriever = KnowledgeBaseRetriever(
            knowledge_base_id=self.config.knowledge_base_id,
            boto_session=self.boto_session,
            region_name=self.config.region_name,
            top_k=self.config.rag_top_k
        )

    def chat(
        self,
        user_message: str,
        session: SessionMemory | None = None
    ) -> AgentResponse:
        """
        Process a single turn of user conversation through the AgentCore engine.
        Handles pre-inference safety filtering, RAG retrieval, and multi-turn tool calling.
        """
        if session is None:
            session = SessionMemory(max_turns=self.config.max_turns)

        # 1. Pre-inference Guardrail & Safety Evaluation
        safety_check = self.guardrail.evaluate_input(user_message)
        if not safety_check.is_safe:
            session.add_user_message(user_message)
            session.add_assistant_message([{"text": safety_check.message}])
            return AgentResponse(
                text=safety_check.message,
                tool_calls=[],
                stop_reason="guardrail_intervened",
                session_id=session.session_id
            )

        # 2. Dynamic Knowledge Base RAG Retrieval
        retrieved_chunks = self.retriever.retrieve(user_message, top_k=self.config.rag_top_k)
        grounded_system_prompt = [{"text": get_system_prompt(retrieved_chunks=retrieved_chunks)}]

        session.add_user_message(user_message)
        tool_calls_recorded: list[ToolCallRecord] = []

        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            if self.config.mock_mode:
                model_output, stop_reason = self._mock_converse_turn(session)
            else:
                converse_kwargs: dict[str, Any] = {
                    "modelId": self.config.model_id,
                    "messages": session.get_messages(),
                    "system": grounded_system_prompt,
                    "toolConfig": self.tool_config,
                    "inferenceConfig": {
                        "temperature": self.config.temperature,
                        "topP": self.config.top_p,
                        "maxTokens": self.config.max_tokens,
                    }
                }
                if self.config.guardrail_id:
                    converse_kwargs["guardrailConfig"] = {
                        "guardrailIdentifier": self.config.guardrail_id,
                        "guardrailVersion": self.config.guardrail_version
                    }
                response = self.bedrock_client.converse(**converse_kwargs)
                model_output = response["output"]["message"]["content"]
                stop_reason = response.get("stopReason", "end_turn")

            # Append assistant message to session memory
            session.add_assistant_message(model_output)

            # Handle tool use if requested by model
            if stop_reason == "tool_use":
                for block in model_output:
                    if "toolUse" in block:
                        tool_use = block["toolUse"]
                        tool_id = tool_use.get("toolUseId", "call_1")
                        tool_name = tool_use.get("name", "")
                        tool_input = tool_use.get("input", {})

                        if tool_name == "create_bug_report":
                            lambda_arn = self.config.lambda_tool_arn if not self.config.mock_mode else None
                            result = execute_bug_report_tool(
                                tool_input,
                                lambda_arn=lambda_arn,
                                boto_session=self.boto_session
                            )
                        else:
                            result = {"status": "ERROR", "error": f"Unknown tool: {tool_name}"}

                        tool_calls_recorded.append(
                            ToolCallRecord(
                                tool_use_id=tool_id,
                                tool_name=tool_name,
                                tool_input=tool_input,
                                tool_result=result
                            )
                        )

                        session.add_tool_result(
                            tool_use_id=tool_id,
                            result_content=result,
                            status="success" if result.get("status") == "SUCCESS" else "error"
                        )
                # Continue loop to allow model to synthesize final response after receiving tool results
                continue

            # If end_turn or finished, extract the text response
            final_text_chunks = [
                block.get("text", "")
                for block in model_output
                if "text" in block
            ]
            final_text = "\n".join(final_text_chunks).strip()

            return AgentResponse(
                text=final_text,
                tool_calls=tool_calls_recorded,
                stop_reason=stop_reason,
                session_id=session.session_id
            )

        return AgentResponse(
            text="I apologize, but I encountered an issue processing your request. Please contact human support at 1-800-555-SHOP.",
            tool_calls=tool_calls_recorded,
            stop_reason="max_iterations",
            session_id=session.session_id
        )

    def _mock_converse_turn(self, session: SessionMemory) -> tuple[list[dict[str, Any]], str]:
        """Offline simulation engine for testing conversational flows and tool execution."""
        messages = session.get_messages()
        last_msg = messages[-1] if messages else {}

        # If last message is toolResult, generate confirmation
        if last_msg.get("role") == "user" and any("toolResult" in b for b in last_msg.get("content", [])):
            for b in last_msg.get("content", []):
                if "toolResult" in b:
                    res = b["toolResult"]["content"][0].get("json", {})
                    ticket_id = res.get("ticketId", "BUG-UNKNOWN")
                    return [
                        {
                            "text": (
                                f"Thank you for reporting this issue. I have filed a support ticket on your behalf "
                                f"(Ticket ID: **{ticket_id}**). Our engineering team has been notified and is "
                                f"investigating the problem."
                            )
                        }
                    ], "end_turn"

        # Aggregate user conversation history
        user_texts = []
        for m in messages:
            if m.get("role") == "user":
                for b in m.get("content", []):
                    if "text" in b:
                        user_texts.append(b["text"])
        all_user_text = " ".join(user_texts).lower()
        latest_text = user_texts[-1].lower() if user_texts else ""

        # Minimal Context / Short Query Edge Cases
        if latest_text.strip() in ("broken", "broken?", "help", "help?"):
            return [
                {
                    "text": (
                        "I'm here to help! Could you please share a few more details about what is broken? "
                        "If a physical product arrived damaged, we can arrange a replacement. If the website "
                        "is experiencing a technical issue, I can file a bug report for you."
                    )
                }
            ], "end_turn"

        # Ambiguous Multi-Intent Edge Cases
        if "return" in latest_text and any(e in latest_text for e in ["crash", "glitch", "error", "bug"]):
            return [
                {
                    "text": (
                        "You can return items within 30 days of delivery. Regarding the website crash on Chrome, "
                        "I would also be glad to log a bug report with our technical support team to resolve this."
                    )
                }
            ], "end_turn"

        if "confirmation" in latest_text and any(e in latest_text for e in ["500", "error", "glitch"]):
            return [
                {
                    "text": (
                        "If your order confirmation email has not arrived within 30 minutes, please check your spam folder "
                        "or contact customer support. We can also record this website server error."
                    )
                }
            ], "end_turn"

        # Intent 1: Bug report detection
        bug_keywords = ["bug", "error", "broken", "crash", "glitch", "doesn't work", "fails", "problem", "defect"]
        is_bug_intent = any(k in all_user_text for k in bug_keywords)

        if is_bug_intent:
            # Check for reproduction steps and environment in conversation
            has_environment = any(e in all_user_text for e in [
                "chrome", "safari", "firefox", "edge", "ios", "iphone", "android", "mac", "windows", "linux", "browser"
            ])
            has_steps = any(s in all_user_text for s in [
                "step", "clicked", "clicking", "when i", "after i", "tried to", "pressed", "added to cart", "checkout"
            ])

            if has_environment and has_steps:
                # All 3 required fields present -> invoke create_bug_report tool
                desc = latest_text if len(latest_text) > 10 else all_user_text[:100]
                env = "Chrome on macOS" if "chrome" in all_user_text or "mac" in all_user_text else "Mobile Browser / iOS"
                steps = "1. Navigate to page 2. Perform action 3. Error observed"
                
                return [
                    {
                        "toolUse": {
                            "toolUseId": f"tooluse_{len(messages)}",
                            "name": "create_bug_report",
                            "input": {
                                "description": desc,
                                "stepsToReproduce": steps,
                                "environment": env
                            }
                        }
                    }
                ], "tool_use"
            else:
                # Missing steps or environment -> ask user for clarification
                missing = []
                if not has_steps:
                    missing.append("the steps to reproduce the problem")
                if not has_environment:
                    missing.append("your device/browser environment (e.g. Chrome on Windows, Safari on iPhone)")

                missing_str = " and ".join(missing)
                return [
                    {
                        "text": (
                            f"I would be glad to file a bug report for you. Could you please provide {missing_str} "
                            f"so our technical team can reproduce and fix the issue?"
                        )
                    }
                ], "end_turn"

        # Intent 2: Platform FAQ Grounding
        if any(k in latest_text for k in ["return", "refund", "exchange"]):
            return [
                {
                    "text": (
                        "You can return most items within 30 days of delivery as long as they are unused and in original "
                        "packaging. Refunds are issued to your original payment method within 3–10 business days after "
                        "we inspect the return. We cover return shipping if the item arrived defective or incorrect."
                    )
                }
            ], "end_turn"

        if any(k in latest_text for k in ["shipping", "delivery", "track", "tracking", "package", "how long"]):
            return [
                {
                    "text": (
                        "We ship to most regions listed at checkout. Processing takes 1–2 business days before dispatch. "
                        "Once shipped, you will receive a tracking link via email. If your package has not arrived 24 hours "
                        "after being marked delivered, please reach out to us. Tracking is also accessible under My Orders."
                    )
                }
            ], "end_turn"

        if any(k in latest_text for k in ["payment", "pay", "credit card", "declined", "invoice", "receipt"]):
            return [
                {
                    "text": (
                        "We accept major credit/debit cards and supported local methods at checkout. You are charged when "
                        "your order is placed. An itemized invoice receipt is emailed immediately after checkout."
                    )
                }
            ], "end_turn"

        if any(k in latest_text for k in ["password", "account", "login", "reset", "email"]):
            return [
                {
                    "text": (
                        "You can reset your password using the 'Forgot password' link on the sign-in page. To update your "
                        "saved address or email, please visit Account Settings."
                    )
                }
            ], "end_turn"

        # Intent 3: Out of Scope / Human Redirection
        return [
            {
                "text": (
                    "I am specialized in assisting with Online Shop orders, shipping, returns, and technical bug reports. "
                    "For inquiries outside these areas, please contact our human support team at 1-800-555-SHOP "
                    "(Monday–Friday, 9am–5pm EST) or via the contact form on our website."
                )
            }
        ], "end_turn"
