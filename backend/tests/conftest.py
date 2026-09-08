"""Pytest fixtures and environment setup for Customer Support Chatbot tests."""

import os

import boto3
import pytest
from moto import mock_aws

# Ensure tests run with predictable mock settings
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing-key"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing-secret"
os.environ["AWS_SECURITY_TOKEN"] = "testing-token"
os.environ["AWS_SESSION_TOKEN"] = "testing-session-token"
os.environ["TABLE_NAME"] = "support-bug-reports-test"
os.environ["AWS_MOCK_MODE"] = "true"
os.environ["CREATE_BUG_REPORT_LAMBDA_ARN"] = ""


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(scope="function")
def dynamodb_table(aws_credentials):
    """Create a mock DynamoDB BugReports table."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName=os.environ["TABLE_NAME"],
            KeySchema=[{"AttributeName": "ticketId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "ticketId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        yield table
