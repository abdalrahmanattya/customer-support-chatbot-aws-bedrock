#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/aws-common.sh
source "${SCRIPT_DIR}/aws-common.sh"
ENVIRONMENT="${1:-demo}"
REGION="${2:-${AWS_REGION:-us-east-1}}"
CONFIRMATION="${3:-}"
STACK_NAME="$(stack_name "$ENVIRONMENT")"

require_command aws
CALLER_ARN="$(verify_identity "$REGION")"
[[ "$CONFIRMATION" == "$STACK_NAME" ]] || {
  echo "Refusing teardown. Re-run with the exact stack name as argument 3:" >&2
  echo "./scripts/teardown.sh ${ENVIRONMENT} ${REGION} ${STACK_NAME}" >&2
  exit 2
}
echo "Deleting ${STACK_NAME} in ${REGION} as ${CALLER_ARN}."
for output_key in WebBucketName KnowledgeDocumentsBucketName; do
  bucket="$(stack_output "$STACK_NAME" "$output_key" "$REGION")"
  aws s3 rm "s3://${bucket}" --recursive --region "$REGION" --only-show-errors
done
aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"
aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ARTIFACT_BUCKET="support-assistant-artifacts-${ACCOUNT_ID}-${REGION}"
aws s3 rm "s3://${ARTIFACT_BUCKET}/${ENVIRONMENT}/" --recursive \
  --region "$REGION" --only-show-errors || true
echo "Deleted ${STACK_NAME}; the shared artifact bucket was retained for other environments."
