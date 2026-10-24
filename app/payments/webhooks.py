import hashlib
import hmac
import logging
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.kafka import producer
from app.metrics import WEBHOOK_ERRORS, WEBHOOK_REQUESTS
from app.models import LedgerEntry, Order, OrderStatus, WebhookEvent
from app.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class PaymentData(BaseModel):
    order_id: UUID
    payment_id: str
    amount: Decimal
    currency: str


class PaymentEvent(BaseModel):
    id: str
    type: Literal["payment.succeeded"]
    created_at: datetime
    data: PaymentData


def verify_signature(body: bytes, signature: str) -> None:
    expected = hmac.new(
        settings.PAYMENT_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    supplied = signature.removeprefix("sha256=")

    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="Invalid signature")


@router.post("/webhooks/payments")
async def receive_payment_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    signature: str = Header(alias="X-Payment-Signature"),
):
    body = await request.body()
    verify_signature(body, signature)

    event = PaymentEvent.model_validate_json(body)

    logger.info("Payment webhook received: %s", body.decode())

    try:
        duplicate = await process_payment_succeeded(db, event)
    except Exception as exc:
        WEBHOOK_ERRORS.labels(event_type=event.type).inc()
        logger.error("Could not process payment webhook: %s", exc)

        # Avoid making the provider retry events we have already received.
        return {"received": True}

    WEBHOOK_REQUESTS.labels(
        event_type=event.type,
        order_id=str(event.data.order_id),
    ).inc()

    return {"received": True, "duplicate": duplicate}


async def process_payment_succeeded(
    db: AsyncSession,
    event: PaymentEvent,
) -> bool:
    existing_event = await db.scalar(
        select(WebhookEvent).where(
            WebhookEvent.provider_event_id == event.id
        )
    )

    if existing_event is not None:
        return True

    db.add(
        WebhookEvent(
            id=uuid4(),
            provider_event_id=event.id,
            event_type=event.type,
            payload=event.model_dump(mode="json"),
            received_at=datetime.utcnow(),
        )
    )
    await db.flush()

    order = await db.scalar(
        select(Order).where(Order.id == event.data.order_id)
    )

    if order is None:
        raise ValueError(f"Order not found: {event.data.order_id}")

    if event.data.amount != order.total_amount:
        logger.warning(
            "Amount mismatch for order %s: expected %s, received %s",
            order.id,
            order.total_amount,
            event.data.amount,
        )

    if order.status == OrderStatus.PAID:
        await db.commit()
        return False

    if order.status != OrderStatus.PENDING:
        logger.info(
            "Ignoring payment for order %s in status %s",
            order.id,
            order.status,
        )
        await db.commit()
        return False

    order.status = OrderStatus.PAID
    order.provider_payment_id = event.data.payment_id
    order.paid_at = datetime.utcnow()

    db.add(
        LedgerEntry(
            id=uuid4(),
            order_id=order.id,
            provider_payment_id=event.data.payment_id,
            entry_type="PAYMENT_CONFIRMED",
            amount=event.data.amount,
            currency=event.data.currency,
            created_at=datetime.utcnow(),
        )
    )

    await db.commit()

    producer.send(
        "payment.confirmed",
        key=str(order.id).encode(),
        value={
            "event_id": event.id,
            "order_id": str(order.id),
            "payment_id": event.data.payment_id,
            "amount": str(event.data.amount),
            "currency": event.data.currency,
        },
    ).get(timeout=10)

    return False
