# AWS readiness review — 2026-09-08

This is read-only readiness evidence, not deployment evidence. The review used a
temporary assumed role in the intended AWS account and `us-east-1`. It did not
create, update, invoke, ingest, or delete resources.

## Result

The target account is ready for a bounded deployment after two known legacy
orphans are handled. CloudFormation accepted `infra/template.yaml`; its public
resource schemas for S3 Vectors, Bedrock Knowledge Bases, and versioned Bedrock
Guardrails are live in the Region. Amazon Nova Pro, the US Nova Pro inference
profile, and Titan Text Embeddings V2 all reported active. IAM policy simulation
allowed the tested create, pass-role, invoke/retrieve, and teardown actions.

No active project CloudFormation stack, DynamoDB table, Lambda function, SQS
queue, S3 bucket, HTTP API, Cognito user pool, Bedrock Flow, Knowledge Base,
Guardrail, S3 vector bucket, CloudFront distribution, or project-tagged resource
was found.

## Findings

- A legacy Bedrock Flow execution role remains although no Bedrock Flow or its
  referenced Lambda function exists. It was last used during the earlier cloud
  experiment and has one inline policy with broad model invocation permission.
- A legacy Lambda log group remains although its Lambda function no longer
  exists. It contains less than one kilobyte and has no retention policy.
- Historical CloudFormation records confirm that the earlier issue/evaluation,
  safety/knowledge, and Flow stacks were deleted.
- The account Lambda concurrency quota is 10. Fixed function reservations were
  therefore removed from the template; API throttling, SQS backpressure, the
  account quota, and per-session usage limits remain the bounded controls.

The two legacy orphans were not deleted because this phase was read-only.
Deletion requires an exact approval naming both resources.

## Reproduction

Run the maintained read-only inventory after assuming temporary credentials:

```bash
source <(./scripts/refresh-credentials.sh)
./scripts/inventory.sh us-east-1
```

Do not treat empty inventory output as proof that a future deployment succeeded;
live acceptance still requires the documented deployment and lifecycle checks.
