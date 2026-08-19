"""Bug Report Tool definition and execution logic for Amazon Bedrock AgentCore."""

import json
import logging
from typing import Any

from src.agent.tools.lambda_handler import lambda_handler

logger = logging.getLogger(__name__)

# Bedrock Converse API Tool Specification
BUG_REPORT_TOOL_SPEC: dict[str, Any] = {
    "toolSpec": {
        "name": "create_bug_report",
        "description": (
            "Submit a confirmed customer-reported website bug or software malfunction to the engineering "
            "ticketing system. Requires a detailed description, reproduction steps, and user environment."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Detailed explanation of what the user experienced or what went wrong."
                    },
                    "stepsToReproduce": {
                        "type": "string",
                        "description": "Step-by-step actions that caused the error to happen."
                    },
                    "environment": {
                        "type": "string",
                        "description": "Operating system, device, or browser where the issue occurred (e.g., Safari on iOS, Chrome on Windows 11)."
                    }
                },
                "required": ["description", "stepsToReproduce", "environment"]
            }
        }
    }
}


def execute_bug_report_tool(
    input_params: dict[str, Any],
    lambda_arn: str | None = None,
    boto_session: Any = None
) -> dict[str, Any]:
    """
    Execute the bug report tool either locally or via AWS Lambda invocation.
    
    Args:
        input_params: The tool parameters extracted by Bedrock model.
        lambda_arn: Optional ARN of deployed Lambda function.
        boto_session: Optional boto3 Session for remote AWS invocation.

    Returns:
        Structured result dict.
    """
    if lambda_arn and boto_session:
        try:
            client = boto_session.client("lambda")
            response = client.invoke(
                FunctionName=lambda_arn,
                Payload=json.dumps(input_params)
            )
            payload = json.loads(response["Payload"].read())
            if isinstance(payload, dict) and "body" in payload:
                return payload["body"] if isinstance(payload["body"], dict) else json.loads(payload["body"])
            return payload
        except Exception as exc:
            logger.error("Error invoking remote Lambda for bug report: %s", exc)
            return {"status": "ERROR", "error": str(exc)}

    # Local in-process execution
    resp = lambda_handler(input_params)
    return resp.get("body", resp)
