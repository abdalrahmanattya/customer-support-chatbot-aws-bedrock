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

---

## 2. Bug Report Path (Bedrock Agent & Tool Calling)

### 2.1 Agent Action Group Configuration
- **File**: `4_agent_action_group_config.jpg`
- **Description**: Agent builder configuration showing `BugReportAgent` with the `BugReportActionGroup` connected to Lambda `support-create-bug-report-dev` and OpenAPI operation `createBugReport` (`description`, `stepsToReproduce`, `environment`).

### 2.2 Complete Bug Report Test Execution
- **File**: `5_flow_test_complete_bug_report.jpg`
- **Description**: Flow test execution panel demonstrating automated ticket creation (`BUG-8F4C2A19`) with full parameters provided in a single turn and tool execution confirmation badge.

### 2.3 Bug Report Multi-Turn Follow-Up Clarification
- **File**: `6_flow_test_bug_report_follow_up.jpg`
- **Description**: Flow test execution panel demonstrating multi-turn clarification questions for incomplete defect reports before successfully executing the ticket creation tool (`BUG-5D1B8E32`).

### 2.4 DynamoDB BugReports Table Items
- **File**: `7_dynamodb_bugreports_table.jpg`
- **Description**: Amazon DynamoDB Explore Items view showing confirmed bug reports stored in `support-bug-reports-dev` with partition key `ticketId`, timestamp, description, environment, and reproduction steps.

---

## 3. Platform Question & Other Request Paths

### 3.1 FAQ Prompt Node Template
- **File**: `8_faq_prompt_node_template.jpg`
- **Description**: Configuration panel for `FAQKnowledgeNode` displaying system instructions with embedded store FAQ documentation (Return Policy, Shipping, Payment Methods) and strict grounding rules.

### 3.2 Covered FAQ Question Test Response
- **File**: `9_flow_test_covered_faq_question.jpg`
- **Description**: Flow test execution panel demonstrating verified answers to covered inquiries (Return Policy: 30 days, unworn, tags attached, 5-7 business days refund) with 420ms latency.

### 3.3 Uncovered FAQ Question Test Response
- **File**: `10_flow_test_uncovered_faq_question.jpg`
- **Description**: Flow test execution panel demonstrating fallback deflection when an inquiry is not covered in store documentation (Corporate bulk discounts -> contact 1-800-555-SHOP / support@onlineshop.com).

### 3.4 Out-of-Scope Other Request Deflection
- **File**: `11_flow_test_other_request_deflection.jpg`
- **Description**: Flow test execution panel demonstrating polite deflection for general out-of-scope requests (e.g. Python script / unrelated task -> polite redirect to support phone line / contact page).
