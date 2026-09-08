"""Business-level tests for customer sessions, queued chat, and tickets."""

from datetime import UTC, datetime, timedelta

import boto3
import pytest
from moto import mock_aws
from support_service.config import AgentConfig
from support_service.core import CustomerSupportAgent
from support_service.product import (
    DynamoProductStore,
    JobStatus,
    MemoryProductStore,
    MemoryQueue,
    ProductError,
    SupportBackend,
    TicketStatus,
)


@pytest.fixture
def backend():
    return SupportBackend(MemoryProductStore(), MemoryQueue(), daily_chat_limit=2)


def session_credentials(backend):
    session, token = backend.create_session()
    return session.session_id, token


def test_session_tokens_isolate_customer_records(backend):
    session_id, token = session_credentials(backend)
    other_id, other_token = session_credentials(backend)
    draft = backend.create_draft(session_id, token, "Checkout freezes", "Click pay", "Chrome")
    ticket = backend.confirm_draft(session_id, token, draft.draft_id, "confirm-1")

    assert backend.get_ticket(session_id, token, ticket.ticket_id) == ticket
    with pytest.raises(ProductError) as denied:
        backend.get_ticket(other_id, other_token, ticket.ticket_id)
    assert denied.value.status == 404
    with pytest.raises(ProductError) as wrong_token:
        backend.get_ticket(session_id, "wrong", ticket.ticket_id)
    assert wrong_token.value.status == 403


def test_expired_session_is_rejected():
    current = datetime(2026, 9, 8, tzinfo=UTC)
    backend = SupportBackend(
        MemoryProductStore(), MemoryQueue(), now=lambda: current, session_ttl=timedelta(minutes=1)
    )
    session, token = backend.create_session()
    current += timedelta(minutes=2)
    with pytest.raises(ProductError) as error:
        backend.submit_chat(session.session_id, token, "hello", "one")
    assert error.value.status == 401


def test_chat_is_queued_idempotently_and_limited(backend):
    session_id, token = session_credentials(backend)
    first = backend.submit_chat(session_id, token, "Return policy?", "message-1")
    repeated = backend.submit_chat(session_id, token, "different text", "message-1")
    backend.submit_chat(session_id, token, "Shipping time?", "message-2")

    assert first.request_id == repeated.request_id
    assert backend.queue.request_ids == [first.request_id, backend.queue.request_ids[1]]
    with pytest.raises(ProductError) as limited:
        backend.submit_chat(session_id, token, "One more", "message-3")
    assert limited.value.status == 429


def test_worker_completes_job_with_citations_and_history(backend):
    session_id, token = session_credentials(backend)
    job = backend.submit_chat(session_id, token, "What is the return policy?", "chat-1")
    agent = CustomerSupportAgent(AgentConfig(mock_mode=True))

    completed = backend.process_chat(job.request_id, agent)

    assert completed.status == JobStatus.COMPLETE
    assert "30 days" in completed.response
    assert completed.citations
    assert backend.get_chat(session_id, token, job.request_id).status == JobStatus.COMPLETE


def test_ticket_requires_confirmation_and_confirmation_is_idempotent(backend):
    session_id, token = session_credentials(backend)
    draft = backend.create_draft(session_id, token, "Checkout freezes", "Click pay", "Chrome")
    assert backend.list_tickets() == []

    ticket = backend.confirm_draft(session_id, token, draft.draft_id, "confirm-1")
    repeated = backend.confirm_draft(session_id, token, draft.draft_id, "confirm-1")

    assert ticket.ticket_id == repeated.ticket_id
    assert len(backend.list_tickets()) == 1


def test_operator_status_transitions_are_ordered(backend):
    session_id, token = session_credentials(backend)
    draft = backend.create_draft(session_id, token, "Checkout freezes", "Click pay", "Chrome")
    ticket = backend.confirm_draft(session_id, token, draft.draft_id, "confirm-1")

    active = backend.update_ticket(ticket.ticket_id, TicketStatus.IN_PROGRESS)
    resolved = backend.update_ticket(ticket.ticket_id, TicketStatus.RESOLVED)

    assert active.status == TicketStatus.IN_PROGRESS
    assert resolved.status == TicketStatus.RESOLVED
    with pytest.raises(ProductError) as invalid:
        backend.update_ticket(ticket.ticket_id, TicketStatus.OPEN)
    assert invalid.value.status == 409


def test_failed_agent_call_has_safe_public_error(backend):
    session_id, token = session_credentials(backend)
    job = backend.submit_chat(session_id, token, "Hello", "chat-1")

    class BrokenAgent:
        class Retriever:
            def retrieve(self, _message):
                raise RuntimeError("secret dependency details")

        retriever = Retriever()

    failed = backend.process_chat(job.request_id, BrokenAgent())
    assert failed.status == JobStatus.FAILED
    assert failed.error == "The support assistant is temporarily unavailable."


def test_dynamodb_adapter_persists_session_and_idempotent_ticket():
    with mock_aws():
        table = boto3.resource("dynamodb", region_name="us-east-1").create_table(
            TableName="support-product-test",
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"},
                       {"AttributeName": "sk", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"},
                                  {"AttributeName": "sk", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        backend = SupportBackend(DynamoProductStore(table), MemoryQueue())
        session, token = backend.create_session()
        draft = backend.create_draft(
            session.session_id, token, "Checkout froze", "Clicked pay", "Chrome"
        )
        first = backend.confirm_draft(session.session_id, token, draft.draft_id, "confirm-one")
        repeated = backend.confirm_draft(session.session_id, token, draft.draft_id, "confirm-one")

        assert first.ticket_id == repeated.ticket_id
        assert backend.get_ticket(session.session_id, token, first.ticket_id) == first
