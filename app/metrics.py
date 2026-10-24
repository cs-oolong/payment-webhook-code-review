from prometheus_client import Counter

WEBHOOK_REQUESTS = Counter(
    "payment_webhook_requests_total",
    "Payment webhooks received",
    ["event_type", "order_id"],
)

WEBHOOK_ERRORS = Counter(
    "payment_webhook_errors_total",
    "Payment webhook processing errors",
    ["event_type"],
)
