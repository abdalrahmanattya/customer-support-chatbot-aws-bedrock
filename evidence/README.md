# Architecture & Configuration Evidence

This directory contains visual architectural and configuration captures for the Customer Support Chatbot implementation on Amazon Bedrock.

---

## 1. Bedrock Flow Classification & Routing

### 1.1 Full Flow Diagram
- **File**: `1_full_flow_diagram.jpg`
- **Description**: Visual canvas showing the complete flow from `FlowInput` -> `IntentClassifierPrompt` -> `RouteByIntent` (Condition Node) branching into `BugReportAgent`, `FAQKnowledgeNode`, and `OutofScopeDeflection` -> `FlowOutput`.

### 1.2 Classifier Prompt Configuration
- **File**: `2_classifier_prompt_config.jpg`
- **Description**: Inspector panel for the `IntentClassifierPrompt` node showing model selection (`Amazon Nova Pro`), system classification instructions for `BUG_REPORT`, `PLATFORM_QUESTION`, and `OTHER_REQUEST`, input variable mapping (`customer_message`), and output variable (`classified_intent`).

### 1.3 Condition Node Expressions
- **File**: `3_condition_node_expressions.jpg`
- **Description**: Inspector panel for the `RouteByIntent` Condition Node showing the JSONPath branching expressions (`$.data contains 'BUG_REPORT'`, `$.data contains 'PLATFORM_QUESTION'`, and `$.data contains 'OTHER_REQUEST'` / Default).
