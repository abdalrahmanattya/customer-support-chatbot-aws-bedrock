# Project Journal

## Current resume point
All 4 advanced features (Bedrock Guardrails safety filter, expanded 22-case edge evaluation benchmark, Bedrock Knowledge Base RAG vector retriever with dynamic prompting, and structured output intent classification) are implemented, verified, and tested with 100% pass rates across unit tests and eval suites. Web UI and server are operational on port 8000.

## Log
- 2026-08-17 — Initialized `customer-support-chatbot-aws-bedrock` repository. Configured local governance and baseline architecture.
- 2026-08-17 — Modernized architecture to Amazon Bedrock AgentCore (ADR-001). Implemented CloudFormation infrastructure stacks for DynamoDB bug report storage, Lambda execution, and S3 Bedrock evaluation dataset store.
- 2026-08-17 — Implemented AgentCore conversational engine with multi-turn tool calling for bug reports, FAQ grounding context, out-of-scope deflection, and session memory trimming.
- 2026-08-17 — Built pytest suite with moto mocks, cfn-lint validation, and automated LLM-as-a-judge evaluation harness (`eval/evaluate_agent.py` and `eval/generate_eval_dataset.py`).
- 2026-08-17 — Added interactive CLI chat interface (`src/cli/chat.py`) with offline mock and live Bedrock modes, deployment scripts (`scripts/deploy.sh`, `scripts/teardown.sh`, `scripts/run-eval.sh`), and updated user documentation.
- 2026-08-18 — Deployed CloudFormation stacks to AWS (`us-east-1`). Successfully executed live end-to-end test with Amazon Bedrock Nova Pro and verified ticket persistence in DynamoDB table `support-bug-reports-dev-us-east-1`.
- 2026-08-18 — Added responsive Web Chat server and user interface (`src/web/server.py`, `scripts/start-web.sh`) with real-time tool badges, quick chips, and live Bedrock integration.
- 2026-08-19 — Implemented Bedrock Guardrail stack (`infrastructure/guardrail-stack.yaml`) and pre-inference safety filter (`src/agent/guardrails/safety_filter.py`) to block prompt injections, jailbreaks, and PII leaks.
- 2026-08-19 — Expanded evaluation suite (`eval/flow-tests.json` & `eval/test_cases.json`) to 22 test cases covering ambiguous multi-intent, minimal context, and adversarial prompt edge-cases (100% accuracy).
- 2026-08-19 — Implemented Bedrock Knowledge Base RAG infrastructure (`infrastructure/knowledge-base-stack.yaml`) and vector retriever (`src/agent/rag/retriever.py`) with dynamic chunk injection.
- 2026-08-19 — Implemented Structured Output Intent Classifier (`src/agent/classifier.py` and `src/agent/models/intent.py`) enforcing Pydantic enum validation via Bedrock tool forcing. All 26 unit tests passing.
