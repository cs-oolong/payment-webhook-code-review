# Payment webhook code review exercise

This repository contains a fictional pull request for a code review interview. Review the open PR as you would review a teammate's changes in a real production repository.

## Your task

Leave review comments on the pull request, prioritizing issues you would block before merge. Explain the concrete failure scenario and impact of each important comment. You do not need to implement fixes.

This is intentionally not a style-review exercise. Consider correctness, reliability, data integrity, concurrency, idempotency, and production operability.

## Context

The service uses FastAPI, asynchronous SQLAlchemy, PostgreSQL, and Kafka. The change adds a payment provider webhook that should:

1. Record the provider event for deduplication.
2. Mark the corresponding order as `PAID`.
3. Create a ledger entry.
4. Publish `payment.confirmed` for downstream services.

## Contracts and assumptions

- The provider delivers events **at least once**.
- The provider retries after an HTTP `5xx` response or when the endpoint takes more than 5 seconds to respond.
- Events can arrive out of order and on different workers.
- The same payment can appear in more than one event, occasionally with different event IDs.
- Other application flows can cancel or refund orders.
- The endpoint is subscribed only to `payment.succeeded` events.
- The signature is the hex HMAC-SHA256 of the raw request body, sent in `X-Payment-Signature` as `sha256=<digest>`.
- Possible order statuses are `PENDING`, `PAID`, `CANCELLED`, and `REFUNDED`.

## Local setup

```bash
python -m pip install -e '.[test]'
pytest
```

The code and all entities in this exercise are fictional.
