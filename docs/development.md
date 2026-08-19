# Development Guide

## Overview
This document tracks local setup, testing, linting, evaluation, and deployment workflows for the Customer Support Chatbot service powered by Amazon Bedrock AgentCore.

## Prerequisites
- Python 3.12+
- AWS CLI v2 configured (required for deployment and live Bedrock testing)
- `pip` / `venv` package management

## Local Setup Workflow
1. Create virtual environment and activate:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies in editable mode:
   ```bash
   pip install -e .
   ```

## Testing & Quality Assurance

### 1. Run Unit Tests (Pytest + Moto)
```bash
pytest tests/ -v
```

### 2. Linting & Formatting
```bash
ruff check src/ tests/ eval/
```

### 3. CloudFormation Validation (cfn-lint)
```bash
cfn-lint infrastructure/*.yaml
```

### 4. Golden Test Suite & Evaluation Benchmark
```bash
./scripts/run-eval.sh --mock
```

## Interactive CLI Chat
Run interactive conversation simulation in terminal:
```bash
# Offline mock mode:
python -m src.cli.chat --mock

# Live AWS Bedrock mode (requires AWS credentials):
python -m src.cli.chat --model amazon.nova-pro-v1:0
```

## AWS Deployment Workflow
Deploy CloudFormation stacks:
```bash
./scripts/deploy.sh dev us-east-1
```

Tear down resources when finished:
```bash
./scripts/teardown.sh dev us-east-1
```
