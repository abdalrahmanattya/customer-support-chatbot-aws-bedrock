# AWS deployment and teardown

The AWS environment is a disposable demonstration, not an always-on service.
The default deployment is `customer-support-assistant-demo` in `us-east-1`,
uses on-demand/serverless resources, limits Lambda concurrency and API request
rates, and stops issuing new customer sessions seven days after deployment.
Expiry limits use; it does not delete resources. Always run teardown.

## Prerequisites

- AWS CLI v2, Python 3.12+, Node.js 22+, npm, and `zip`
- An AWS principal allowed to manage the resources in `infra/template.yaml`
- Amazon Nova Pro and Titan Text Embeddings V2 available in the target Region
- S3 Vectors and Bedrock Knowledge Bases available in the target Region

Use temporary credentials. The local-only helper follows the same STS
AssumeRole pattern as the companion support project and prints shell exports;
it neither commits credentials nor writes them to `.env`:

```bash
source <(./scripts/refresh-credentials.sh)
aws sts get-caller-identity
```

Review the identity before any mutation. Then deploy:

```bash
./scripts/deploy.sh demo us-east-1
```

The script builds a Lambda zip, uploads it to a private bootstrap artifact
bucket, deploys the CloudFormation stack, uploads and starts ingestion of the
fictional policy document, builds the web app with stack outputs, publishes it
to the private web bucket, and requests a CloudFront invalidation. Stack outputs
are copied to ignored `.aws-outputs/`; they are local diagnostics, not public
deployment evidence.

## Operator access

Public registration is disabled. Invite a bounded operator only when an email
recipient is available:

```bash
./scripts/create-operator.sh demo us-east-1 operator@example.com
```

Cognito sends a temporary-password invitation. The user is added to the
`operators` group, which is checked by both API Gateway JWT authorization and
the backend claims boundary.

## Verification

Wait until the knowledge ingestion job succeeds, then run:

```bash
./scripts/verify-deployment.sh demo us-east-1
```

This verifies public health and web endpoints and saves a sanitized stack
summary locally. Full acceptance additionally covers a grounded customer chat,
ticket confirmation, operator sign-in, and ordered ticket status transitions.

## Teardown

Teardown requires the exact stack name to reduce accidental deletion:

```bash
./scripts/teardown.sh demo us-east-1 customer-support-assistant-demo
```

The script empties both stack-owned S3 buckets, deletes and waits for the stack,
and deletes only this environment's Lambda artifacts. It deletes the bootstrap
artifact bucket when that bucket is empty; if another environment still has
artifacts, it preserves the shared bucket.

## GitHub Actions

CI never deploys. The `AWS demo lifecycle` workflow is manual-only and uses
GitHub OIDC. Configure an `aws-demo` GitHub environment with required reviewers
and the environment variable `AWS_DEPLOY_ROLE_ARN`; do not store long-lived AWS
keys in GitHub. Select exactly `deploy`, `verify`, or `teardown` when dispatching
the workflow.
