#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/aws-common.sh
source "${SCRIPT_DIR}/aws-common.sh"
ROOT_DIR="$(project_root)"
ENVIRONMENT="${1:-demo}"
REGION="${2:-${AWS_REGION:-us-east-1}}"
STACK_NAME="$(stack_name "$ENVIRONMENT")"
EVIDENCE_DIR="${ROOT_DIR}/.aws-outputs"

require_command aws
require_command curl
mkdir -p "$EVIDENCE_DIR"
API_URL="$(stack_output "$STACK_NAME" ApiUrl "$REGION")"
WEB_URL="$(stack_output "$STACK_NAME" WebUrl "$REGION")"
HEALTH_STATUS="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' "${API_URL}/health")"
WEB_STATUS="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' "$WEB_URL")"
[[ "$HEALTH_STATUS" == "200" ]] || { echo "API health returned ${HEALTH_STATUS}" >&2; exit 1; }
[[ "$WEB_STATUS" == "200" ]] || { echo "Web endpoint returned ${WEB_STATUS}" >&2; exit 1; }
aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" \
  --query '{stack:Stacks[0].StackName,status:Stacks[0].StackStatus,outputs:Stacks[0].Outputs}' \
  --output json >"${EVIDENCE_DIR}/${STACK_NAME}-verification.json"
echo "Verified API ${API_URL} and web ${WEB_URL}."
