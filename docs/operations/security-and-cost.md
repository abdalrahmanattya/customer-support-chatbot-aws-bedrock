# Security, cost, and failure controls

## Security boundaries

- Customer sessions receive random bearer tokens; only SHA-256 token hashes are
  persisted, records are session-scoped, and sessions expire.
- Operator routes require a Cognito JWT at API Gateway and membership in the
  `operators` group in the Lambda handler. Self-registration is disabled.
- The web and knowledge buckets block public access. CloudFront reads web assets
  through Origin Access Control.
- Lambda roles separate API persistence/queue permissions from worker inference
  permissions. The Knowledge Base has a separate service role and a vector
  bucket policy restricted to that role.
- Bedrock Guardrails and local input checks provide defense in depth. Application
  logs and API access logs intentionally omit request bodies and bearer tokens.
- Temporary STS credentials and generated stack outputs are ignored locally.

This system uses fictional policies and synthetic tickets. Do not submit real
payment, identity, account, or customer data.

## Cost envelope

The architecture avoids fixed-capacity databases and vector clusters. DynamoDB
is on demand; Lambda, HTTP API, SQS, Bedrock inference, Knowledge Base retrieval,
S3 Vectors, S3, and CloudFront charge primarily with use. API throttles, queue
backpressure, the account concurrency quota, a per-session chat limit, seven-day
log retention, short object lifecycle rules, and a deployment expiry reduce
runaway or forgotten-demo risk.

Expiry is not teardown. CloudFront, stored objects/vectors, alarms, and other
resources can continue to incur charges until the stack is deleted. Review the
current AWS pricing pages and account budgets before deployment because service
prices and free-tier eligibility vary by Region and date.

## Failure behavior

- SQS retries transient worker failures three times, then isolates messages in a
  four-day dead-letter queue. An alarm detects visible dead-letter messages.
- Customer polling returns a safe generic failure; dependency details remain in
  CloudWatch logs.
- Ticket confirmation and chat submission use idempotency keys.
- CloudFormation owns product resources and deletion policy is explicit. S3
  buckets must be emptied before teardown; the script performs that bounded step.
- Knowledge ingestion is asynchronous. A deployment is not accepted until its
  ingestion job and the end-to-end journeys pass.
