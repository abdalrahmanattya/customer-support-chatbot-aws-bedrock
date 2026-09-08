#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/aws-common.sh
source "${SCRIPT_DIR}/aws-common.sh"
REGION="${1:-${AWS_REGION:-us-east-1}}"

require_command aws
echo "Read-only inventory in ${REGION} as $(verify_identity "$REGION")"

echo "CloudFormation stacks"
aws cloudformation list-stacks --region "$REGION" \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE UPDATE_ROLLBACK_COMPLETE ROLLBACK_COMPLETE \
  --query "StackSummaries[?contains(StackName, 'support')].[StackName,StackStatus]" --output table

echo "DynamoDB tables"
aws dynamodb list-tables --region "$REGION" \
  --query "TableNames[?contains(@, 'support') || contains(@, 'Support')]" --output json
echo "Lambda functions"
aws lambda list-functions --region "$REGION" \
  --query "Functions[?contains(FunctionName, 'support') || contains(FunctionName, 'Support')].[FunctionName,Runtime]" --output json
echo "SQS queues"
aws sqs list-queues --region "$REGION" \
  --query "QueueUrls[?contains(@, 'support') || contains(@, 'Support')]" --output json
echo "S3 buckets"
aws s3api list-buckets \
  --query "Buckets[?contains(Name, 'support') || contains(Name, 'bedrock')].Name" --output json
echo "HTTP APIs"
aws apigatewayv2 get-apis --region "$REGION" \
  --query "Items[?contains(Name, 'support') || contains(Name, 'Support')].[Name,ApiId]" --output json
echo "Cognito user pools"
aws cognito-idp list-user-pools --max-results 60 --region "$REGION" \
  --query "UserPools[?contains(Name, 'support') || contains(Name, 'Support')].[Name,Id]" --output json
echo "Bedrock flows, knowledge bases, and guardrails"
aws bedrock-agent list-flows --region "$REGION" \
  --query "flowSummaries[?contains(name, 'upport')].[name,id,status]" --output json
aws bedrock-agent list-knowledge-bases --region "$REGION" \
  --query "knowledgeBaseSummaries[?contains(name, 'upport')].[name,knowledgeBaseId,status]" --output json
aws bedrock list-guardrails --region "$REGION" \
  --query "guardrails[?contains(name, 'upport')].[name,id,status]" --output json
echo "S3 vector buckets"
aws s3vectors list-vector-buckets --region "$REGION" \
  --query "vectorBuckets[?contains(vectorBucketName, 'support')].[vectorBucketName,vectorBucketArn]" --output json
echo "IAM roles and CloudWatch log groups"
aws iam list-roles \
  --query "Roles[?contains(RoleName, 'support') || contains(RoleName, 'Support')].[RoleName,CreateDate]" --output json
aws logs describe-log-groups --region "$REGION" \
  --query "logGroups[?contains(logGroupName, 'support') || contains(logGroupName, 'Support')].[logGroupName,retentionInDays,storedBytes]" --output json
