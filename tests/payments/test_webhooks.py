import pytest
from sqlalchemy import select

from app.models import LedgerEntry, OrderStatus
from app.payments.webhooks import process_payment_succeeded


@pytest.mark.asyncio
async def test_confirms_pending_order(db, order, payment_event, producer_mock):
    result = await process_payment_succeeded(db, payment_event)

    assert result is False
    assert order.status == OrderStatus.PAID
    assert order.provider_payment_id == payment_event.data.payment_id

    entries = (
        await db.scalars(
            select(LedgerEntry).where(LedgerEntry.order_id == order.id)
        )
    ).all()
    assert len(entries) == 1
    assert entries[0].amount == order.total_amount

    producer_mock.send.assert_called_once()


@pytest.mark.asyncio
async def test_ignores_duplicate_event(
    db,
    paid_order,
    payment_event,
    stored_webhook_event,
    producer_mock,
):
    result = await process_payment_succeeded(db, payment_event)

    assert result is True
    producer_mock.send.assert_not_called()


@pytest.mark.asyncio
async def test_does_not_replace_terminal_order_status(
    db,
    cancelled_order,
    payment_event,
    producer_mock,
):
    result = await process_payment_succeeded(db, payment_event)

    assert result is False
    assert cancelled_order.status == OrderStatus.CANCELLED
    producer_mock.send.assert_not_called()
