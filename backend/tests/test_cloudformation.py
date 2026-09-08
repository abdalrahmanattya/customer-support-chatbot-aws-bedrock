"""Structural tests for the cohesive disposable AWS deployment."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT_DIR / "infra" / "template.yaml"


def template_text() -> str:
    assert TEMPLATE.exists()
    return TEMPLATE.read_text(encoding="utf-8")


def test_template_contains_complete_serverless_product():
    content = template_text()
    for resource_type in (
        "AWS::ApiGatewayV2::Api",
        "AWS::Lambda::Function",
        "AWS::SQS::Queue",
        "AWS::DynamoDB::Table",
        "AWS::Cognito::UserPool",
        "AWS::CloudFront::Distribution",
        "AWS::S3::Bucket",
    ):
        assert resource_type in content


def test_template_contains_native_grounding_and_safety_resources():
    content = template_text()
    for resource_type in (
        "AWS::Bedrock::KnowledgeBase",
        "AWS::Bedrock::DataSource",
        "AWS::Bedrock::Guardrail",
        "AWS::Bedrock::GuardrailVersion",
        "AWS::S3Vectors::VectorBucket",
        "AWS::S3Vectors::Index",
    ):
        assert resource_type in content


def test_template_encodes_disposable_cost_controls():
    content = template_text()
    assert "BillingMode: PAY_PER_REQUEST" in content
    assert "ThrottlingRateLimit: 5" in content
    assert "BatchSize: 5" in content
    assert "DemoExpiresAt" in content
    assert "DeletionPolicy: Delete" in content
    assert "TimeToLiveSpecification" in content
