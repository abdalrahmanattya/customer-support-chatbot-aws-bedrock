#!/usr/bin/env bash
# ==============================================================================
# Customer Support Chatbot - AWS CloudFormation Teardown Script
# ==============================================================================
set -euo pipefail

ENVIRONMENT="${1:-dev}"
REGION="${2:-us-east-1}"
TOOL_STACK_NAME="support-bug-report-stack-${ENVIRONMENT}"
EVAL_STACK_NAME="support-eval-stack-${ENVIRONMENT}"

echo "=================================================================="
echo " Tearing down Customer Support Chatbot Infrastructure"
echo " Environment: ${ENVIRONMENT}"
echo " Region:      ${REGION}"
echo "=================================================================="

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed or not found in PATH." >&2
    exit 1
fi

read -p "Are you sure you want to delete stacks ${TOOL_STACK_NAME} and ${EVAL_STACK_NAME}? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Teardown canceled."
    exit 0
fi

# 1. Delete Evaluation Stack
echo "--> Deleting Evaluation Stack (${EVAL_STACK_NAME})..."
aws cloudformation delete-stack --stack-name "${EVAL_STACK_NAME}" --region "${REGION}"

# 2. Delete Tool Stack
echo "--> Deleting Tool Stack (${TOOL_STACK_NAME})..."
aws cloudformation delete-stack --stack-name "${TOOL_STACK_NAME}" --region "${REGION}"

echo "Waiting for stacks to be deleted..."
aws cloudformation wait stack-delete-complete --stack-name "${TOOL_STACK_NAME}" --region "${REGION}" || true
aws cloudformation wait stack-delete-complete --stack-name "${EVAL_STACK_NAME}" --region "${REGION}" || true

echo "=================================================================="
echo " Infrastructure cleanup complete."
echo "=================================================================="
