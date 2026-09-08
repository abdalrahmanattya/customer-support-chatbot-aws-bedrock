"""HTTP Lambda adapter tests for authentication and route behavior."""

import json

from support_service import runtime
from support_service.product import MemoryProductStore, MemoryQueue, SupportBackend


def event(method, path, *, body=None, token=None, idempotency=None, operator=False):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if idempotency:
        headers["Idempotency-Key"] = idempotency
    claims = {"cognito:groups": "operators"} if operator else {}
    return {
        "rawPath": path,
        "headers": headers,
        "body": json.dumps(body) if body is not None else None,
        "requestContext": {"http": {"method": method}, "authorizer": {"jwt": {"claims": claims}}},
    }


def test_customer_api_queues_and_reads_only_own_job(monkeypatch):
    backend = SupportBackend(MemoryProductStore(), MemoryQueue())
    monkeypatch.setattr(runtime, "build_backend", lambda: backend)
    created = json.loads(runtime.api_handler(event("POST", "/sessions"))["body"])

    queued_response = runtime.api_handler(
        event("POST", f"/sessions/{created['sessionId']}/messages",
              body={"message": "Return policy?"}, token=created["sessionToken"],
              idempotency="chat-one")
    )
    queued = json.loads(queued_response["body"])
    fetched = runtime.api_handler(
        event("GET", f"/sessions/{created['sessionId']}/messages/{queued['request_id']}",
              token=created["sessionToken"])
    )

    assert queued_response["statusCode"] == 202
    assert fetched["statusCode"] == 200
    assert json.loads(fetched["body"])["status"] == "PENDING"


def test_health_route(monkeypatch):
    backend = SupportBackend(MemoryProductStore(), MemoryQueue())
    monkeypatch.setattr(runtime, "build_backend", lambda: backend)

    response = runtime.api_handler(event("GET", "/health"))

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"status": "ok"}


def test_operator_routes_require_verified_group(monkeypatch):
    backend = SupportBackend(MemoryProductStore(), MemoryQueue())
    monkeypatch.setattr(runtime, "build_backend", lambda: backend)

    denied = runtime.api_handler(event("GET", "/operator/tickets"))
    allowed = runtime.api_handler(event("GET", "/operator/tickets", operator=True))

    assert denied["statusCode"] == 403
    assert allowed["statusCode"] == 200
    assert json.loads(allowed["body"]) == {"tickets": []}


def test_ticket_api_requires_explicit_confirmation(monkeypatch):
    backend = SupportBackend(MemoryProductStore(), MemoryQueue())
    monkeypatch.setattr(runtime, "build_backend", lambda: backend)
    created = json.loads(runtime.api_handler(event("POST", "/sessions"))["body"])
    base = f"/sessions/{created['sessionId']}"
    draft_response = runtime.api_handler(
        event("POST", f"{base}/ticket-drafts", token=created["sessionToken"],
              body={"description": "Checkout froze", "stepsToReproduce": "Clicked pay",
                    "environment": "Chrome"})
    )
    draft = json.loads(draft_response["body"])
    assert backend.list_tickets() == []

    ticket_response = runtime.api_handler(
        event("POST", f"{base}/ticket-drafts/{draft['draft_id']}/confirm",
              token=created["sessionToken"], idempotency="confirm-one")
    )

    assert ticket_response["statusCode"] == 201
    assert len(backend.list_tickets()) == 1
