"""AWS adapters and Lambda handlers for the support product."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any

import boto3

from support_service.config import AgentConfig
from support_service.core import CustomerSupportAgent
from support_service.product import (
    DynamoProductStore,
    ProductError,
    SqsQueue,
    SupportBackend,
    TicketStatus,
)


def build_backend() -> SupportBackend:
    table_name = os.environ["PRODUCT_TABLE_NAME"]
    queue_url = os.environ["CHAT_QUEUE_URL"]
    region = os.environ.get("AWS_REGION", "us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name=region)
    sqs = boto3.client("sqs", region_name=region)
    expires_at = os.environ.get("DEMO_EXPIRES_AT")
    return SupportBackend(
        DynamoProductStore(dynamodb.Table(table_name)),
        SqsQueue(sqs, queue_url),
        daily_chat_limit=int(os.environ.get("DAILY_CHAT_LIMIT", "30")),
        demo_expires_at=datetime.fromisoformat(expires_at)
        if expires_at
        else None,
    )


def _response(status: int, body: Any) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json", "cache-control": "no-store"},
        "body": json.dumps(body, default=str),
    }


def _body(event: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as exc:
        raise ProductError("Request body must be valid JSON.") from exc
    if not isinstance(value, dict):
        raise ProductError("Request body must be a JSON object.")
    return value


def _customer_token(event: dict[str, Any]) -> str:
    headers = {key.lower(): value for key, value in event.get("headers", {}).items()}
    auth = headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise ProductError("A session bearer token is required.", 401)
    return auth.removeprefix("Bearer ").strip()


def _idempotency_key(event: dict[str, Any]) -> str:
    headers = {key.lower(): value for key, value in event.get("headers", {}).items()}
    key = headers.get("idempotency-key", "").strip()
    if not key or len(key) > 128:
        raise ProductError("A valid Idempotency-Key header is required.")
    return key


def _require_operator(event: dict[str, Any]) -> None:
    claims = (
        event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    )
    groups = claims.get("cognito:groups", "")
    if isinstance(groups, str):
        groups = [part.strip() for part in groups.strip("[]").split(",") if part.strip()]
    if "operators" not in groups:
        raise ProductError("Operator access required.", 403)


def api_handler(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    backend = build_backend()
    method = event.get("requestContext", {}).get("http", {}).get("method", event.get("httpMethod", ""))
    path = event.get("rawPath", event.get("path", ""))
    try:
        if method == "GET" and path == "/health":
            return _response(200, {"status": "ok"})
        if method == "POST" and path == "/sessions":
            session, token = backend.create_session()
            return _response(201, {"sessionId": session.session_id, "sessionToken": token,
                                   "expiresAt": session.expires_at})

        match = re.fullmatch(r"/sessions/([^/]+)/messages", path)
        if method == "POST" and match:
            body = _body(event)
            job = backend.submit_chat(match.group(1), _customer_token(event),
                                      str(body.get("message", "")), _idempotency_key(event))
            return _response(202, job.model_dump(mode="json"))

        match = re.fullmatch(r"/sessions/([^/]+)/messages/([^/]+)", path)
        if method == "GET" and match:
            job = backend.get_chat(match.group(1), _customer_token(event), match.group(2))
            return _response(200, job.model_dump(mode="json"))

        match = re.fullmatch(r"/sessions/([^/]+)/ticket-drafts", path)
        if method == "POST" and match:
            body = _body(event)
            draft = backend.create_draft(match.group(1), _customer_token(event),
                                         str(body.get("description", "")),
                                         str(body.get("stepsToReproduce", "")),
                                         str(body.get("environment", "")))
            return _response(201, draft.model_dump(mode="json"))

        match = re.fullmatch(r"/sessions/([^/]+)/ticket-drafts/([^/]+)/confirm", path)
        if method == "POST" and match:
            ticket = backend.confirm_draft(match.group(1), _customer_token(event), match.group(2),
                                           _idempotency_key(event))
            return _response(201, ticket.model_dump(mode="json"))

        match = re.fullmatch(r"/sessions/([^/]+)/tickets/([^/]+)", path)
        if method == "GET" and match:
            ticket = backend.get_ticket(match.group(1), _customer_token(event), match.group(2))
            return _response(200, ticket.model_dump(mode="json"))

        if path == "/operator/tickets" and method == "GET":
            _require_operator(event)
            status = (event.get("queryStringParameters") or {}).get("status")
            tickets = backend.list_tickets(TicketStatus(status) if status else None)
            return _response(200, {"tickets": [item.model_dump(mode="json") for item in tickets]})

        match = re.fullmatch(r"/operator/tickets/([^/]+)", path)
        if match and method == "GET":
            _require_operator(event)
            return _response(200, backend.operator_ticket(match.group(1)).model_dump(mode="json"))
        if match and method == "PATCH":
            _require_operator(event)
            ticket = backend.update_ticket(match.group(1), TicketStatus(_body(event).get("status")))
            return _response(200, ticket.model_dump(mode="json"))
        raise ProductError("Route not found.", 404)
    except ProductError as exc:
        return _response(exc.status, {"error": exc.message})
    except (ValueError, TypeError):
        return _response(400, {"error": "Request contains an invalid value."})


def worker_handler(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    backend = build_backend()
    agent = CustomerSupportAgent(config=AgentConfig())
    failures = []
    for record in event.get("Records", []):
        try:
            request_id = json.loads(record["body"])["requestId"]
            backend.process_chat(request_id, agent)
        except Exception:
            failures.append({"itemIdentifier": record.get("messageId", "unknown")})
    return {"batchItemFailures": failures}
