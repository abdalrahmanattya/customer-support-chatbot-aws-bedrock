"""Unit tests for FAQ knowledge base grounding and system prompt generation."""

from src.agent.prompts.system_prompt import get_faq_content, get_system_prompt


def test_faq_file_loaded():
    """Verify FAQ text is loaded and contains essential sections."""
    faq = get_faq_content()
    assert len(faq) > 500
    assert "Orders" in faq
    assert "Shipping & Delivery" in faq
    assert "Returns & Refunds" in faq
    assert "Payments & Promotions" in faq
    assert "30 days" in faq
    assert "1-800-555-SHOP" in faq


def test_system_prompt_structure():
    """Verify generated system prompt incorporates rules, tool instructions, and FAQ grounding."""
    prompt = get_system_prompt()
    assert "Customer Support Assistant" in prompt
    assert "BUG REPORTS (Tool Use)" in prompt
    assert "create_bug_report" in prompt
    assert "stepsToReproduce" in prompt
    assert "environment" in prompt
    assert "PLATFORM & POLICY QUESTIONS" in prompt
    assert "OUT-OF-SCOPE INQUIRIES & ESCALATION" in prompt
    assert "KNOWLEDGE BASE" in prompt
