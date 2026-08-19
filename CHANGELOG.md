# Changelog

## [1.1.0] - 2026-08-19
### Added
- Standalone responsive Web Chat UI & Server (`src/web/server.py`, `scripts/start-web.sh`) with live Bedrock streaming, quick action chips, and real-time tool badges.
- Amazon Bedrock Guardrail stack (`infrastructure/guardrail-stack.yaml`) and pre-inference safety filter (`src/agent/guardrails/safety_filter.py`) for prompt injection, jailbreak, and PII defense.
- Expanded 22-case edge evaluation benchmark suite (`eval/flow-tests.json` & `eval/test_cases.json`) covering ambiguous multi-intent, minimal context, and prompt attacks with 100% accuracy.
- Bedrock Knowledge Base RAG infrastructure stack (`infrastructure/knowledge-base-stack.yaml`) and TF-IDF/vector similarity retriever (`src/agent/rag/retriever.py`) with dynamic chunk injection.
- Structured Output Intent Classifier (`src/agent/classifier.py`, `src/agent/models/intent.py`) enforcing Pydantic enum validation using Bedrock tool forcing.
- 12 new unit and integration tests across guardrails, classifier, and RAG retrieval (26/26 tests passing).

## [1.0.0] - 2026-08-17
### Added
- Bedrock AgentCore Assistant engine (`src/agent/core.py`) with support for Amazon Nova and Anthropic Claude foundation models.
- Session memory and conversation history manager (`src/agent/session.py`) with automatic context trimming.
- Grounded e-commerce FAQ knowledge base (`src/agent/prompts/online_shop_faq.md`) and system prompt builder (`src/agent/prompts/system_prompt.py`).
- Bug report tool specification and Lambda handler with DynamoDB ticket persistence (`src/agent/tools/`).
- AWS CloudFormation templates for Bug Report storage & execution (`infrastructure/tool-stack.yaml`) and Bedrock Evaluations (`infrastructure/eval-stack.yaml`).
- Interactive rich CLI chat interface (`src/cli/chat.py`) supporting offline mock and live cloud execution.
- Automated evaluation harness (`eval/evaluate_agent.py` and `eval/generate_eval_dataset.py`) producing Bedrock Evaluations BYOI format.
- Comprehensive test suite in `tests/` with unit, mock, and CloudFormation template validation.
- Deployment and evaluation automation scripts in `scripts/`.
- Architectural Decision Record (`docs/decisions/ADR-001-bedrock-agentcore-modernization.md`).

## [0.1.0-dev] - 2026-08-17
- Initial repository scaffolding, architecture specification, and context baseline.
