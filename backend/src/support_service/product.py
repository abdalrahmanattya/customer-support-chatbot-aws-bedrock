"""Application services for persistent chat sessions and support tickets."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field

from support_service.core import CustomerSupportAgent
from support_service.session import SessionMemory


class ProductError(Exception):
    """Base error carrying an HTTP-compatible status and public message."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


class JobStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class TicketStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class SessionRecord(BaseModel):
    session_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime
    usage_count: int = 0
    messages: list[dict[str, Any]] = Field(default_factory=list)


class ChatJob(BaseModel):
    request_id: str
    session_id: str
    message: str
    status: JobStatus = JobStatus.PENDING
    response: str | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class TicketDraft(BaseModel):
    draft_id: str
    session_id: str
    description: str
    steps_to_reproduce: str
    environment: str
    created_at: datetime
    expires_at: datetime


class Ticket(BaseModel):
    ticket_id: str
    session_id: str
    description: str
    steps_to_reproduce: str
    environment: str
    status: TicketStatus = TicketStatus.OPEN
    created_at: datetime
    updated_at: datetime


class ProductStore(Protocol):
    def get(self, kind: str, record_id: str) -> dict[str, Any] | None: ...
    def put(self, kind: str, record_id: str, value: dict[str, Any]) -> None: ...
    def list(self, kind: str) -> list[dict[str, Any]]: ...
    def get_idempotency(self, scope: str, key: str) -> str | None: ...
    def put_idempotency(self, scope: str, key: str, value: str) -> bool: ...


class MemoryProductStore:
    """Thread-safe deterministic store for local development and tests."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], dict[str, Any]] = {}
        self._idempotency: dict[tuple[str, str], str] = {}
        self._lock = threading.Lock()

    def get(self, kind: str, record_id: str) -> dict[str, Any] | None:
        with self._lock:
            value = self._records.get((kind, record_id))
            return json.loads(json.dumps(value, default=str)) if value else None

    def put(self, kind: str, record_id: str, value: dict[str, Any]) -> None:
        with self._lock:
            self._records[(kind, record_id)] = json.loads(json.dumps(value, default=str))

    def list(self, kind: str) -> list[dict[str, Any]]:
        with self._lock:
            return [
                json.loads(json.dumps(value, default=str))
                for (record_kind, _), value in self._records.items()
                if record_kind == kind
            ]

    def get_idempotency(self, scope: str, key: str) -> str | None:
        with self._lock:
            return self._idempotency.get((scope, key))

    def put_idempotency(self, scope: str, key: str, value: str) -> bool:
        with self._lock:
            pair = (scope, key)
            if pair in self._idempotency:
                return False
            self._idempotency[pair] = value
            return True


class DynamoProductStore:
    """Single-table DynamoDB adapter used by API and worker Lambdas."""

    def __init__(self, table: Any):
        self.table = table

    @staticmethod
    def _key(kind: str, record_id: str) -> dict[str, str]:
        return {"pk": f"{kind}#{record_id}", "sk": "RECORD"}

    def get(self, kind: str, record_id: str) -> dict[str, Any] | None:
        item = self.table.get_item(Key=self._key(kind, record_id)).get("Item")
        return json.loads(item["payload"]) if item else None

    def put(self, kind: str, record_id: str, value: dict[str, Any]) -> None:
        item = {
            **self._key(kind, record_id),
            "kind": kind,
            "payload": json.dumps(value, default=str),
        }
        expires_at = value.get("expires_at")
        if expires_at:
            parsed = datetime.fromisoformat(str(expires_at))
            item["expiresAtEpoch"] = int(parsed.timestamp())
        self.table.put_item(Item=item)

    def list(self, kind: str) -> list[dict[str, Any]]:
        from boto3.dynamodb.conditions import Attr

        items: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {"FilterExpression": Attr("kind").eq(kind)}
        while True:
            response = self.table.scan(**kwargs)
            items.extend(json.loads(item["payload"]) for item in response.get("Items", []))
            if "LastEvaluatedKey" not in response:
                return items
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    def get_idempotency(self, scope: str, key: str) -> str | None:
        item = self.table.get_item(Key=self._key("IDEMPOTENCY", f"{scope}#{key}")).get("Item")
        return item.get("value") if item else None

    def put_idempotency(self, scope: str, key: str, value: str) -> bool:
        try:
            self.table.put_item(
                Item={
                    **self._key("IDEMPOTENCY", f"{scope}#{key}"),
                    "value": value,
                    "expiresAtEpoch": int((datetime.now(UTC) + timedelta(days=1)).timestamp()),
                },
                ConditionExpression="attribute_not_exists(pk)",
            )
            return True
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            return False


class MessageQueue(Protocol):
    def send(self, request_id: str) -> None: ...


class MemoryQueue:
    def __init__(self) -> None:
        self.request_ids: list[str] = []

    def send(self, request_id: str) -> None:
        self.request_ids.append(request_id)


class SqsQueue:
    def __init__(self, client: Any, queue_url: str):
        self.client = client
        self.queue_url = queue_url

    def send(self, request_id: str) -> None:
        self.client.send_message(QueueUrl=self.queue_url, MessageBody=json.dumps({"requestId": request_id}))


class SupportBackend:
    """Business rules shared by local execution and AWS Lambda handlers."""

    def __init__(
        self,
        store: ProductStore,
        queue: MessageQueue,
        *,
        now: Callable[[], datetime] | None = None,
        session_ttl: timedelta = timedelta(hours=2),
        daily_chat_limit: int = 30,
        demo_expires_at: datetime | None = None,
    ) -> None:
        self.store = store
        self.queue = queue
        self.now = now or (lambda: datetime.now(UTC))
        self.session_ttl = session_ttl
        self.daily_chat_limit = daily_chat_limit
        self.demo_expires_at = demo_expires_at

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def create_session(self) -> tuple[SessionRecord, str]:
        now = self.now()
        if self.demo_expires_at and now >= self.demo_expires_at:
            raise ProductError("This demonstration deployment has expired.", 503)
        token = secrets.token_urlsafe(32)
        session = SessionRecord(
            session_id=str(uuid.uuid4()), token_hash=self._token_hash(token),
            created_at=now, expires_at=now + self.session_ttl,
        )
        self.store.put("SESSION", session.session_id, session.model_dump(mode="json"))
        return session, token

    def require_session(self, session_id: str, token: str) -> SessionRecord:
        raw = self.store.get("SESSION", session_id)
        if not raw:
            raise ProductError("Session not found.", 404)
        session = SessionRecord.model_validate(raw)
        if session.expires_at <= self.now():
            raise ProductError("Session has expired.", 401)
        if not hmac.compare_digest(session.token_hash, self._token_hash(token)):
            raise ProductError("Session access denied.", 403)
        return session

    def submit_chat(self, session_id: str, token: str, message: str, key: str) -> ChatJob:
        session = self.require_session(session_id, token)
        message = message.strip()
        if not message or len(message) > 2000:
            raise ProductError("Message must contain between 1 and 2000 characters.")
        prior = self.store.get_idempotency(f"CHAT#{session_id}", key)
        if prior:
            return ChatJob.model_validate(self.store.get("JOB", prior))
        if session.usage_count >= self.daily_chat_limit:
            raise ProductError("This demonstration session has reached its chat limit.", 429)
        request_id = str(uuid.uuid4())
        job = ChatJob(request_id=request_id, session_id=session_id, message=message, created_at=self.now())
        if not self.store.put_idempotency(f"CHAT#{session_id}", key, request_id):
            prior = self.store.get_idempotency(f"CHAT#{session_id}", key)
            return ChatJob.model_validate(self.store.get("JOB", prior))
        session.usage_count += 1
        self.store.put("SESSION", session_id, session.model_dump(mode="json"))
        self.store.put("JOB", request_id, job.model_dump(mode="json"))
        self.queue.send(request_id)
        return job

    def get_chat(self, session_id: str, token: str, request_id: str) -> ChatJob:
        self.require_session(session_id, token)
        raw = self.store.get("JOB", request_id)
        if not raw or raw.get("session_id") != session_id:
            raise ProductError("Chat request not found.", 404)
        return ChatJob.model_validate(raw)

    def process_chat(self, request_id: str, agent: CustomerSupportAgent) -> ChatJob:
        raw = self.store.get("JOB", request_id)
        if not raw:
            raise ProductError("Chat request not found.", 404)
        job = ChatJob.model_validate(raw)
        if job.status != JobStatus.PENDING:
            return job
        session = SessionRecord.model_validate(self.store.get("SESSION", job.session_id))
        memory = SessionMemory(session_id=session.session_id)
        memory.messages = session.messages
        try:
            citations = [
                {"id": chunk.chunk_id, "title": chunk.title, "score": chunk.score}
                for chunk in agent.retriever.retrieve(job.message)
            ]
            response = agent.chat(job.message, session=memory)
            job.status = JobStatus.COMPLETE
            job.response = response.text
            job.citations = citations
            session.messages = memory.messages
            self.store.put("SESSION", session.session_id, session.model_dump(mode="json"))
        except Exception:
            job.status = JobStatus.FAILED
            job.error = "The support assistant is temporarily unavailable."
        job.completed_at = self.now()
        self.store.put("JOB", request_id, job.model_dump(mode="json"))
        return job

    def create_draft(
        self, session_id: str, token: str, description: str, steps: str, environment: str
    ) -> TicketDraft:
        self.require_session(session_id, token)
        fields = [description.strip(), steps.strip(), environment.strip()]
        if any(not value or len(value) > 2000 for value in fields):
            raise ProductError("Description, reproduction steps, and environment are required.")
        now = self.now()
        draft = TicketDraft(
            draft_id=str(uuid.uuid4()), session_id=session_id, description=fields[0],
            steps_to_reproduce=fields[1], environment=fields[2], created_at=now,
            expires_at=now + timedelta(minutes=30),
        )
        self.store.put("DRAFT", draft.draft_id, draft.model_dump(mode="json"))
        return draft

    def confirm_draft(self, session_id: str, token: str, draft_id: str, key: str) -> Ticket:
        self.require_session(session_id, token)
        prior = self.store.get_idempotency(f"TICKET#{session_id}", key)
        if prior:
            return Ticket.model_validate(self.store.get("TICKET", prior))
        raw = self.store.get("DRAFT", draft_id)
        if not raw or raw.get("session_id") != session_id:
            raise ProductError("Ticket draft not found.", 404)
        draft = TicketDraft.model_validate(raw)
        if draft.expires_at <= self.now():
            raise ProductError("Ticket draft has expired.", 410)
        now = self.now()
        ticket = Ticket(
            ticket_id=f"SUP-{uuid.uuid4().hex[:8].upper()}", session_id=session_id,
            description=draft.description, steps_to_reproduce=draft.steps_to_reproduce,
            environment=draft.environment, created_at=now, updated_at=now,
        )
        if not self.store.put_idempotency(f"TICKET#{session_id}", key, ticket.ticket_id):
            prior = self.store.get_idempotency(f"TICKET#{session_id}", key)
            return Ticket.model_validate(self.store.get("TICKET", prior))
        self.store.put("TICKET", ticket.ticket_id, ticket.model_dump(mode="json"))
        return ticket

    def get_ticket(self, session_id: str, token: str, ticket_id: str) -> Ticket:
        self.require_session(session_id, token)
        raw = self.store.get("TICKET", ticket_id)
        if not raw or raw.get("session_id") != session_id:
            raise ProductError("Ticket not found.", 404)
        return Ticket.model_validate(raw)

    def list_tickets(self, status: TicketStatus | None = None) -> list[Ticket]:
        tickets = [Ticket.model_validate(item) for item in self.store.list("TICKET")]
        return sorted(
            (ticket for ticket in tickets if status is None or ticket.status == status),
            key=lambda ticket: ticket.created_at, reverse=True,
        )

    def operator_ticket(self, ticket_id: str) -> Ticket:
        raw = self.store.get("TICKET", ticket_id)
        if not raw:
            raise ProductError("Ticket not found.", 404)
        return Ticket.model_validate(raw)

    def update_ticket(self, ticket_id: str, status: TicketStatus) -> Ticket:
        ticket = self.operator_ticket(ticket_id)
        allowed = {
            TicketStatus.OPEN: {TicketStatus.IN_PROGRESS},
            TicketStatus.IN_PROGRESS: {TicketStatus.RESOLVED},
            TicketStatus.RESOLVED: set(),
        }
        if status not in allowed[ticket.status]:
            raise ProductError(f"Cannot move ticket from {ticket.status} to {status}.", 409)
        ticket.status = status
        ticket.updated_at = self.now()
        self.store.put("TICKET", ticket_id, ticket.model_dump(mode="json"))
        return ticket
