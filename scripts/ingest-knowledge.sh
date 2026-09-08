#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/aws-common.sh
source "${SCRIPT_DIR}/aws-common.sh"
ROOT_DIR="$(project_root)"
ENVIRONMENT="${1:-demo}"
REGION="${2:-${AWS_REGION:-us-east-1}}"
STACK_NAME="$(stack_name "$ENVIRONMENT")"

require_command aws
BUCKET="$(stack_output "$STACK_NAME" KnowledgeDocumentsBucketName "$REGION")"
KB_ID="$(stack_output "$STACK_NAME" KnowledgeBaseId "$REGION")"
DATA_SOURCE_ID="$(stack_output "$STACK_NAME" KnowledgeDataSourceId "$REGION")"
aws s3 sync "${ROOT_DIR}/knowledge/policies/" "s3://${BUCKET}/policies/" \
  --delete --region "$REGION" --only-show-errors
JOB_ID="$(aws bedrock-agent start-ingestion-job --knowledge-base-id "$KB_ID" \
  --data-source-id "$DATA_SOURCE_ID" --region "$REGION" \
  --query 'ingestionJob.ingestionJobId' --output text)"
echo "Knowledge ingestion started: ${JOB_ID}"
for _ in {1..90}; do
  STATUS="$(aws bedrock-agent get-ingestion-job --knowledge-base-id "$KB_ID" \
    --data-source-id "$DATA_SOURCE_ID" --ingestion-job-id "$JOB_ID" --region "$REGION" \
    --query 'ingestionJob.status' --output text)"
  case "$STATUS" in
    COMPLETE)
      echo "Knowledge ingestion completed."
      exit 0
      ;;
    FAILED | STOPPED)
      echo "Knowledge ingestion ended with status ${STATUS}." >&2
      exit 1
      ;;
  esac
  sleep 10
done
echo "Knowledge ingestion did not complete within 15 minutes." >&2
exit 1
