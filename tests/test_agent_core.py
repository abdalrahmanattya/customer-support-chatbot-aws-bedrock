"""Unit tests for Bedrock AgentCore Assistant and Session Memory."""

from moto import mock_aws

from src.agent.config import AgentConfig
from src.agent.core import CustomerSupportAgent
from src.agent.session import SessionMemory


def test_session_memory_operations():
    """Test message addition, trimming, and role alternation in SessionMemory."""
    session = SessionMemory(max_turns=3)
    session.add_user_message("Hello")
    session.add_assistant_message([{"text": "Hi there, how can I help you today?"}])
    session.add_user_message("What is your shipping policy?")
    session.add_assistant_message([{"text": "We ship in 1-2 days."}])
    session.add_user_message("Can I return items?")
    session.add_assistant_message([{"text": "Yes within 30 days."}])

    messages = session.get_messages()
    assert len(messages) == 6
    assert messages[0]["role"] == "user"
    assert messages[-1]["role"] == "assistant"

    # Add another message to trigger trimming
    session.add_user_message("Do you have discounts?")
    session.add_assistant_message([{"text": "Yes, enter promo at checkout."}])
    assert len(session.get_messages()) <= 6

    # Test clear
    session.clear()
    assert len(session.get_messages()) == 0


def test_agent_faq_inquiry():
    """Test agent response to a platform FAQ inquiry."""
    config = AgentConfig(mock_mode=True)
    agent = CustomerSupportAgent(config=config)
    session = SessionMemory()

    response = agent.chat("What is your return policy and how long do I have?", session=session)
    assert response.text != ""
    assert "30 days" in response.text
    assert len(response.tool_calls) == 0
    assert response.stop_reason == "end_turn"


def test_agent_incomplete_bug_report_clarification():
    """Test that agent asks for missing information when a bug report is incomplete."""
    config = AgentConfig(mock_mode=True)
    agent = CustomerSupportAgent(config=config)
    session = SessionMemory()

    response = agent.chat("The checkout page has a bug and crashed.", session=session)
    assert len(response.tool_calls) == 0
    assert "steps" in response.text.lower() or "environment" in response.text.lower() or "browser" in response.text.lower()


def test_agent_multi_turn_bug_report_resolution():
    """Test end-to-end multi-turn bug report submission and tool invocation."""
    with mock_aws():
        config = AgentConfig(mock_mode=True)
        agent = CustomerSupportAgent(config=config)
        session = SessionMemory()

        # Turn 1: Incomplete report
        resp1 = agent.chat("I found a bug on the checkout button.", session=session)
        assert len(resp1.tool_calls) == 0

        # Turn 2: Provide missing details (steps and environment)
        resp2 = agent.chat(
            "I am using Chrome on macOS. When I click 'Place Order' after entering my address, it fails.",
            session=session
        )
        assert len(resp2.tool_calls) == 1
        assert resp2.tool_calls[0].tool_name == "create_bug_report"
        assert resp2.tool_calls[0].tool_result.get("status") == "SUCCESS"
        assert "BUG-" in resp2.text


def test_agent_out_of_scope_escalation():
    """Test that out-of-scope requests are politely redirected to human support."""
    config = AgentConfig(mock_mode=True)
    agent = CustomerSupportAgent(config=config)
    session = SessionMemory()

    response = agent.chat("What is the recipe for baking sourdough bread?", session=session)
    assert len(response.tool_calls) == 0
    assert "1-800-555-SHOP" in response.text or "human support" in response.text.lower()
