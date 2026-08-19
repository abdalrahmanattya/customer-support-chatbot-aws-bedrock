#!/usr/bin/env bash
# ==============================================================================
# Customer Support Chatbot - AWS CloudFormation Deployment Script
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source .env if present
if [ -f "${ROOT_DIR}/.env" ]; then
    set -a
    source "${ROOT_DIR}/.env"
    set +a
fi

ENVIRONMENT="${1:-${DEPLOY_ENV:-dev}}"
REGION="${2:-${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}}"
TOOL_STACK_NAME="support-bug-report-stack-${ENVIRONMENT}"
EVAL_STACK_NAME="support-eval-stack-${ENVIRONMENT}"

echo "=================================================================="
echo " Deploying Customer Support Chatbot Infrastructure"
echo " Environment: ${ENVIRONMENT}"
echo " Region:      ${REGION}"
echo "=================================================================="

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed or not found in PATH." >&2
    exit 1
fi

# 1. Deploy Tool Stack (DynamoDB + Lambda + IAM)
echo ""
echo "--> Deploying Tool Stack (${TOOL_STACK_NAME})..."
aws cloudformation deploy \
    --template-file "${ROOT_DIR}/infrastructure/tool-stack.yaml" \
    --stack-name "${TOOL_STACK_NAME}" \
    --parameter-overrides EnvironmentName="${ENVIRONMENT}" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "${REGION}"

# 2. Deploy Evaluation Stack (S3 + Bedrock Eval IAM Role)
echo ""
echo "--> Deploying Evaluation Stack (${EVAL_STACK_NAME})..."
aws cloudformation deploy \
    --template-file "${ROOT_DIR}/infrastructure/eval-stack.yaml" \
    --stack-name "${EVAL_STACK_NAME}" \
    --parameter-overrides EnvironmentName="${ENVIRONMENT}" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "${REGION}"

echo ""
echo "=================================================================="
echo " Deployment completed successfully!"
echo " Outputs:"
aws cloudformation describe-stacks \
    --stack-name "${TOOL_STACK_NAME}" \
    --region "${REGION}" \
    --query "Stacks[0].Outputs" \
    --output table
echo "=================================================================="
