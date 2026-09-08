#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/aws-common.sh
source "${SCRIPT_DIR}/aws-common.sh"
ROOT_DIR="$(project_root)"

ENVIRONMENT="${1:-demo}"
REGION="${2:-${AWS_REGION:-us-east-1}}"
MODEL_ID="${BEDROCK_MODEL_ID:-us.amazon.nova-pro-v1:0}"
EXPIRES_AT="${DEMO_EXPIRES_AT:-$(python3 - <<'PY'
from datetime import UTC, datetime, timedelta
print((datetime.now(UTC) + timedelta(days=7)).replace(microsecond=0).isoformat().replace("+00:00", "Z"))
PY
)}"
STACK_NAME="$(stack_name "$ENVIRONMENT")"
BUILD_DIR="${ROOT_DIR}/.aws-build"
OUTPUT_DIR="${ROOT_DIR}/.aws-outputs"

require_command aws
require_command npm
require_command python3
require_command zip

CALLER_ARN="$(verify_identity "$REGION")"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ARTIFACT_BUCKET="support-assistant-artifacts-${ACCOUNT_ID}-${REGION}"
CODE_KEY="${ENVIRONMENT}/lambda-$(git -C "$ROOT_DIR" rev-parse --short HEAD)-$(date -u +%Y%m%d%H%M%S).zip"

echo "Deploying ${STACK_NAME} in ${REGION} as ${CALLER_ARN}"
echo "New sessions expire at ${EXPIRES_AT}; model is ${MODEL_ID}."

if ! aws s3api head-bucket --bucket "$ARTIFACT_BUCKET" >/dev/null 2>&1; then
  if [[ "$REGION" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "$ARTIFACT_BUCKET" --region "$REGION" >/dev/null
  else
    aws s3api create-bucket --bucket "$ARTIFACT_BUCKET" --region "$REGION" \
      --create-bucket-configuration "LocationConstraint=${REGION}" >/dev/null
  fi
  aws s3api put-public-access-block --bucket "$ARTIFACT_BUCKET" \
    --public-access-block-configuration \
    'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true'
fi

rm -rf "${BUILD_DIR:?}/lambda"
rm -f "${BUILD_DIR}/lambda.zip"
mkdir -p "${BUILD_DIR}/lambda" "$OUTPUT_DIR"
python3 -m pip install --quiet --disable-pip-version-check \
  --requirement "${ROOT_DIR}/backend/requirements.txt" \
  --platform manylinux2014_x86_64 --implementation cp --python-version 3.12 \
  --only-binary=:all: \
  --target "${BUILD_DIR}/lambda"
cp -R "${ROOT_DIR}/backend/src/support_service" "${BUILD_DIR}/lambda/"
mkdir -p "${BUILD_DIR}/lambda/knowledge/policies"
cp "${ROOT_DIR}/knowledge/policies/store-policies.md" \
  "${BUILD_DIR}/lambda/knowledge/policies/"
(
  cd "${BUILD_DIR}/lambda"
  zip -qr "${BUILD_DIR}/lambda.zip" .
)
aws s3 cp "${BUILD_DIR}/lambda.zip" "s3://${ARTIFACT_BUCKET}/${CODE_KEY}" \
  --region "$REGION" --only-show-errors

aws cloudformation deploy \
  --template-file "${ROOT_DIR}/infra/template.yaml" \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset \
  --tags Project=customer-support-assistant Environment="$ENVIRONMENT" Lifecycle=disposable-demo \
  --parameter-overrides EnvironmentName="$ENVIRONMENT" CodeBucket="$ARTIFACT_BUCKET" \
    CodeKey="$CODE_KEY" ModelId="$MODEL_ID" DemoExpiresAt="$EXPIRES_AT"

"${SCRIPT_DIR}/ingest-knowledge.sh" "$ENVIRONMENT" "$REGION"

API_URL="$(stack_output "$STACK_NAME" ApiUrl "$REGION")"
WEB_BUCKET="$(stack_output "$STACK_NAME" WebBucketName "$REGION")"
DISTRIBUTION_ID="$(stack_output "$STACK_NAME" DistributionId "$REGION")"
COGNITO_DOMAIN="$(stack_output "$STACK_NAME" CognitoDomain "$REGION")"
CLIENT_ID="$(stack_output "$STACK_NAME" UserPoolClientId "$REGION")"

VITE_DEMO_MODE=false VITE_API_URL="$API_URL" VITE_COGNITO_DOMAIN="$COGNITO_DOMAIN" \
VITE_COGNITO_CLIENT_ID="$CLIENT_ID" npm --prefix "$ROOT_DIR" run web:build
aws s3 sync "${ROOT_DIR}/apps/web/dist/" "s3://${WEB_BUCKET}/" \
  --delete --region "$REGION" --only-show-errors
aws cloudfront create-invalidation --distribution-id "$DISTRIBUTION_ID" --paths '/*' >/dev/null

aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" \
  --query 'Stacks[0].Outputs' --output json >"${OUTPUT_DIR}/${STACK_NAME}.json"
echo "Deployment complete: $(stack_output "$STACK_NAME" WebUrl "$REGION")"
echo "Create an operator only when needed: ./scripts/create-operator.sh ${ENVIRONMENT} ${REGION} <email>"
echo "Teardown command: ./scripts/teardown.sh ${ENVIRONMENT} ${REGION} ${STACK_NAME}"
