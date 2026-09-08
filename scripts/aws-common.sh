#!/usr/bin/env bash
set -euo pipefail

project_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

stack_name() {
  printf 'customer-support-assistant-%s' "$1"
}

stack_output() {
  local stack="$1"
  local key="$2"
  local region="$3"
  aws cloudformation describe-stacks \
    --stack-name "$stack" \
    --region "$region" \
    --query "Stacks[0].Outputs[?OutputKey=='${key}'].OutputValue | [0]" \
    --output text
}

verify_identity() {
  local region="$1"
  aws sts get-caller-identity --region "$region" --query Arn --output text
}
