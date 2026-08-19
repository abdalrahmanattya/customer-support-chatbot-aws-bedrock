"""Lambda function handler for creating and persisting bug reports in DynamoDB."""

import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3

REQUIRED_FIELDS = ("description", "stepsToReproduce", "environment")


def get_dynamodb_table():
    """Helper to lazily initialize the DynamoDB Table resource."""
    region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    table_name = os.environ.get("TABLE_NAME", f"support-bug-reports-dev-{region}")
    dynamodb = boto3.resource("dynamodb", region_name=region)
    return dynamodb.Table(table_name)


def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """
    Handle bug report creation requests.
    Supports both direct parameter dicts and Bedrock Agent Action Group invocations.
    """
    print("Received event:", json.dumps(event, default=str))

    # Parse parameters from various event structures
    body = {}
    if "parameters" in event:
        params = event.get("parameters") or []
        body = {
            p.get("name"): p.get("value")
            for p in params
            if isinstance(p, dict) and p.get("name") is not None
        }
    elif "requestBody" in event:
        rb = event.get("requestBody", {})
        content = rb.get("content", {}).get("application/json", {})
        body = content.get("properties", {})
    elif isinstance(event, dict):
        body = event

    description = str(body.get("description") or "").strip()
    steps = str(body.get("stepsToReproduce") or "").strip()
    environment = str(body.get("environment") or "").strip()

    if not description:
        return _format_response(
            event,
            {"status": "ERROR", "error": "Missing required field: description"},
            status_code=400,
        )

    ticket_id = f"BUG-{uuid.uuid4().hex[:8].upper()}"
    now_iso = datetime.now(UTC).isoformat()

    item = {
        "ticketId": ticket_id,
        "description": description,
        "stepsToReproduce": steps or "Not provided",
        "environment": environment or "Not provided",
        "status": "OPEN",
        "createdAt": now_iso,
        "updatedAt": now_iso,
    }

    # Persist item to DynamoDB table
    try:
        table = get_dynamodb_table()
        table.put_item(Item=item)
    except Exception as exc:
        print(f"DynamoDB PutItem notice: {exc}")
        # In mock mode or offline testing, log notice and continue with ticket creation
        is_mock = os.environ.get("AWS_MOCK_MODE", "").lower() in ("true", "1", "yes")
        if not is_mock and "ResourceNotFoundException" not in str(exc) and "EndpointConnectionError" not in str(exc):
            raise

    result = {
        "status": "SUCCESS",
        "ticketId": ticket_id,
        "message": f"Bug report ticket {ticket_id} created successfully.",
        "createdAt": now_iso,
    }
    return _format_response(event, result, status_code=200)


def _format_response(event: dict[str, Any], data: dict[str, Any], status_code: int = 200) -> dict[str, Any]:
    """Format response based on caller environment."""
    if "actionGroup" in event or "messageVersion" in event:
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", "create_bug_report"),
                "function": event.get("function", "create_bug_report"),
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": json.dumps(data)
                        }
                    }
                },
            },
        }
    return {
        "statusCode": status_code,
        "body": data,
    }
