# Customer Support Assistant on AWS

An AWS-native support application for a fictional online store. The product is
being developed as two connected experiences: a customer chat that answers
policy questions and captures support issues, and an authenticated operations
desk where staff can review and resolve submitted tickets.

## Purpose

Provide a small, reproducible support workflow that demonstrates grounded AI
answers, controlled escalation, and operator ticket handling on AWS.

## Current capabilities

- Python conversational engine using the Amazon Bedrock Converse API
- Local policy retrieval with optional Bedrock Knowledge Base retrieval
- Structured intent classification and issue extraction
- DynamoDB-backed issue creation function
- Configurable Bedrock Guardrails integration with local safety checks
- Terminal client and a temporary local web client
- Offline tests and a 22-case behavioral evaluation suite
- CloudFormation templates for the existing experimental resources

The React application, operator desk, persistent sessions, asynchronous
processing, and complete disposable AWS deployment are planned and are not
represented as finished features.

## Why it is useful

Customers can receive answers grounded in published store policies and turn a
conversation into a trackable issue when automation is insufficient. Operators
will get a small queue for progressing issues from open to resolved. The
deployment is designed for short demonstrations and complete teardown, keeping
idle AWS cost close to zero.

## Current system architecture

```mermaid
flowchart LR
    Customer[Customer] --> Legacy[Temporary local web client]
    Developer[Developer] --> CLI[Command-line client]
    Legacy --> Engine[Python support engine]
    CLI --> Engine
    Engine --> Safety[Local checks / optional Bedrock Guardrail]
    Engine --> Retrieval[Local policy retrieval / optional Bedrock KB]
    Engine --> Converse[Amazon Bedrock Converse API]
    Engine --> Ticket[Issue creation function]
    Ticket --> DynamoDB[(DynamoDB when configured)]
```

## Planned cloud-resources architecture diagram

```mermaid
flowchart TB
    Customer[Customer browser] --> CloudFront[Amazon CloudFront]
    Operator[Operator browser] --> CloudFront
    CloudFront --> Web[(Private Amazon S3 web assets)]
    Customer --> API[Amazon API Gateway HTTP API]
    Operator --> Cognito[Amazon Cognito]
    Operator --> API
    API --> ApiLambda[API Lambda]
    ApiLambda --> Queue[Amazon SQS]
    Queue --> Worker[Chat worker Lambda]
    Worker --> Bedrock[Amazon Bedrock Converse + Guardrails]
    Worker --> KB[Bedrock Knowledge Bases]
    KB --> Policies[(S3 policies + S3 Vectors)]
    ApiLambda --> Data[(DynamoDB sessions and tickets)]
    Worker --> Data
    ApiLambda --> Logs[Amazon CloudWatch]
    Worker --> Logs
```

## Repository layout

```text
apps/web/                   React customer and operator application (planned)
backend/src/support_service Python service, CLI, and temporary web client
backend/tests/              Backend unit and integration tests
knowledge/policies/         Fictional store policy source
knowledge/fixtures/         Synthetic demonstration data
evals/cases/                Behavioral and safety scenarios
evals/runners/              Offline and live evaluation tools
infra/                      AWS CloudFormation/SAM infrastructure
scripts/                    Local and cloud lifecycle commands
tests/e2e/                  Browser acceptance journeys (planned)
docs/                       Architecture, operations, and verification records
```

## Run locally

Python 3.12 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
ruff check backend evals
cfn-lint infra/*.yaml
./scripts/run-eval.sh --mock
```

Start the temporary browser client with `./scripts/start-web.sh`, or run the
terminal client with `python -m support_service.cli --mock`.

Mock mode is a local simulation. It is not evidence that AWS services or live
persistence are working.

## Exact deployment method

The repository does not yet contain the complete product deployment shown
above. Existing templates under `infra/` cover only the earlier issue-storage,
guardrail, knowledge-document, and evaluation resources. They will be replaced
by a cohesive disposable deployment.

The intended workflow is:

```bash
source <(./scripts/refresh-credentials.sh)
./scripts/deploy.sh demo us-east-1
./scripts/teardown.sh demo us-east-1
```

These commands are not live deployment evidence until the verification report
records a successful deploy, acceptance run, and teardown.

## Deployment status

No current AWS deployment is claimed. The local application baseline is
implemented and tested; the complete AWS architecture is planned. A read-only
AWS inventory will reconcile resources from earlier work before a new
deployment is authorized.

No AWS resources are currently deployed; all AWS resources in the cloud diagram are planned until a live verification record states otherwise.

## Limitations

- Sessions currently live in one process and disappear when the server stops.
- The temporary web client has no operator workflow or Cognito authentication.
- The current knowledge template does not provision a complete managed vector
  knowledge base.
- Offline evaluation uses deterministic simulation and is not a model-quality
  or cloud-availability measurement.
- The fictional product does not connect to commerce, payment, email, or order
  systems.
- Live Bedrock use depends on model availability, quotas, latency, and charges.

## Documentation

- [Architecture](docs/architecture/README.md)
- [Local development](docs/operations/local-development.md)
- [Verification policy](docs/verification/README.md)

## License

This project is available under the MIT License.
