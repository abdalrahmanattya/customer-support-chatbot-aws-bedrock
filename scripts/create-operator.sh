#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/aws-common.sh
source "${SCRIPT_DIR}/aws-common.sh"
ENVIRONMENT="${1:-demo}"
REGION="${2:-${AWS_REGION:-us-east-1}}"
EMAIL="${3:?Usage: ./scripts/create-operator.sh <environment> <region> <email>}"
STACK_NAME="$(stack_name "$ENVIRONMENT")"
USER_POOL_ID="$(stack_output "$STACK_NAME" UserPoolId "$REGION")"

require_command aws
aws cognito-idp admin-create-user --user-pool-id "$USER_POOL_ID" --username "$EMAIL" \
  --user-attributes Name=email,Value="$EMAIL" Name=email_verified,Value=true \
  --desired-delivery-mediums EMAIL --region "$REGION" >/dev/null
aws cognito-idp admin-add-user-to-group --user-pool-id "$USER_POOL_ID" --username "$EMAIL" \
  --group-name operators --region "$REGION"
echo "Operator invitation created for ${EMAIL}."
