# ADR-001: Migration to Amazon Bedrock AgentCore Architecture

## Status
Accepted

## Context
The legacy starter implementation was designed around early iterations of Amazon Bedrock Flows and Bedrock Agents Classic. Bedrock Flows imposed rigid condition matching and lacked fine-grained multi-turn memory control, while Bedrock Agents Classic abstracted the orchestration layer into an opaque, high-latency service with limited local testability and extensibility.

AWS has shifted modern agent development toward **Amazon Bedrock AgentCore** and the **Bedrock Converse API with Tool Use**. AgentCore provides a modular, production-ready runtime architecture with explicit tool calling, deterministic session management, standardized telemetry/observability, and native support for modern foundation models (e.g., Amazon Nova, Anthropic Claude 3.5).

## Decision
We adopt the **Bedrock AgentCore** architecture and the **Bedrock Converse API** for the Customer Support Chatbot:
1. **Agent Orchestration**: Use Bedrock's Converse API (`converse` / `converse_stream`) with structured `toolConfig` and `toolSpec` schemas for precise tool execution and multi-turn conversational memory.
2. **Tool Integration**: Tools (such as `create_bug_report`) are defined with strict JSON schemas and backed by AWS Lambda and DynamoDB.
3. **Knowledge Retrieval**: Platform FAQ knowledge is grounded directly into the system context for high-accuracy tier-1 deflection, with clear boundaries to avoid hallucination.
4. **Infrastructure as Code**: All cloud resources (DynamoDB table, Lambda functions, IAM roles, S3 evaluation buckets) are declared via modular **AWS CloudFormation** templates.
5. **Testing & Evaluation**: Implement an offline mock test harness (`pytest`) and an automated Bedrock Evaluations LLM-as-a-judge dataset generator using the Bring Your Own Inference (BYOI) schema.

## Consequences
### Positive
- Full local testability without requiring live cloud deployments or credentials for unit/mock testing.
- Predictable, deterministic routing and extraction for bug reports and FAQ inquiries.
- Future-proof alignment with AWS Bedrock's modern AgentCore platform.
- Clean separation between infrastructure definition (CloudFormation) and runtime logic (Python 3.12+).

### Negative / Trade-offs
- Requires managing the conversational loop and tool result round-trip in application code rather than via a no-code Flow UI.
- Context window management must account for embedded FAQ tokens alongside conversation history.
