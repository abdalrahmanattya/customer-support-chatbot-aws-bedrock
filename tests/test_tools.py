"""Unit tests for bug report tool and Lambda handler."""

import json

from moto import mock_aws

from src.agent.tools.bug_report import BUG_REPORT_TOOL_SPEC, execute_bug_report_tool
from src.agent.tools.lambda_handler import lambda_handler


def test_tool_spec_structure():
    """Verify tool specification meets Bedrock Converse API standards."""
    assert "toolSpec" in BUG_REPORT_TOOL_SPEC
    spec = BUG_REPORT_TOOL_SPEC["toolSpec"]
    assert spec["name"] == "create_bug_report"
    assert "inputSchema" in spec
    assert "json" in spec["inputSchema"]
    
    schema = spec["inputSchema"]["json"]
    assert schema["type"] == "object"
    assert "description" in schema["properties"]
    assert "stepsToReproduce" in schema["properties"]
    assert "environment" in schema["properties"]
    assert set(schema["required"]) == {"description", "stepsToReproduce", "environment"}


def test_lambda_handler_direct_dict(dynamodb_table):
    """Test Lambda handler with direct dictionary parameters."""
    event = {
        "description": "Payment button unclickable on mobile",
        "stepsToReproduce": "1. Add item 2. Click Pay Now",
        "environment": "iOS Safari 17.4"
    }

    resp = lambda_handler(event)
    assert resp["statusCode"] == 200
    body = resp["body"]
    assert body["status"] == "SUCCESS"
    assert body["ticketId"].startswith("BUG-")
    assert "created successfully" in body["message"]

    # Verify item stored in DynamoDB
    item = dynamodb_table.get_item(Key={"ticketId": body["ticketId"]})["Item"]
    assert item["description"] == event["description"]
    assert item["stepsToReproduce"] == event["stepsToReproduce"]
    assert item["environment"] == event["environment"]
    assert item["status"] == "OPEN"


def test_lambda_handler_action_group_event(dynamodb_table):
    """Test Lambda handler with Bedrock Agent Action Group message format."""
    event = {
        "messageVersion": "1.0",
        "actionGroup": "create_bug_report",
        "function": "create_bug_report",
        "parameters": [
            {"name": "description", "value": "Spinner spins forever"},
            {"name": "stepsToReproduce", "value": "Click submit button"},
            {"name": "environment", "value": "Chrome 122 on Windows 11"}
        ]
    }

    resp = lambda_handler(event)
    assert resp["messageVersion"] == "1.0"
    function_resp = resp["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    parsed = json.loads(function_resp)
    assert parsed["status"] == "SUCCESS"
    assert parsed["ticketId"].startswith("BUG-")


def test_lambda_handler_missing_description(dynamodb_table):
    """Test Lambda handler returns error when description is missing."""
    event = {
        "stepsToReproduce": "Click button",
        "environment": "Chrome"
    }
    resp = lambda_handler(event)
    assert resp["statusCode"] == 400
    assert resp["body"]["status"] == "ERROR"
    assert "Missing required field" in resp["body"]["error"]


def test_execute_bug_report_tool_local():
    """Test execute_bug_report_tool helper execution."""
    with mock_aws():
        params = {
            "description": "Cart items disappear upon refresh",
            "stepsToReproduce": "Add item, reload browser",
            "environment": "Firefox on Linux"
        }
        res = execute_bug_report_tool(params)
        assert res.get("status") == "SUCCESS"
        assert "ticketId" in res
