# HTTP API contract

All bodies use JSON. Customer routes use the opaque bearer token returned when
the session is created. Mutating customer operations that could be retried use
an `Idempotency-Key` header. Operator routes require a verified Cognito JWT in
the `operators` group.

| Method | Route | Result |
|---|---|---|
| `GET` | `/health` | Returns a dependency-light API process health response |
| `POST` | `/sessions` | Creates a short-lived session and returns its bearer token once |
| `POST` | `/sessions/{id}/messages` | Validates and queues chat; returns `202` and a request ID |
| `GET` | `/sessions/{id}/messages/{requestId}` | Returns chat state and citations |
| `POST` | `/sessions/{id}/ticket-drafts` | Stores a 30-minute issue draft for review |
| `POST` | `/sessions/{id}/ticket-drafts/{draftId}/confirm` | Idempotently creates a confirmed ticket |
| `GET` | `/sessions/{id}/tickets/{ticketId}` | Returns a ticket belonging to the session |
| `GET` | `/operator/tickets` | Lists tickets, optionally filtered by status |
| `GET` | `/operator/tickets/{ticketId}` | Returns operator ticket details |
| `PATCH` | `/operator/tickets/{ticketId}` | Advances `OPEN` to `IN_PROGRESS` or then `RESOLVED` |

The public API returns generic dependency errors. Internal exception details are
not persisted in customer-visible job records. API responses use `no-store`.
