from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base, Order, OrderStatus, WebhookEvent
from app.payments.webhooks import PaymentData, PaymentEvent

ORDER_ID = UUID("11111111-1111-1111-1111-111111111111")
EVENT_ID = "evt_01J8EXAMPLE"


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def payment_event():
    return PaymentEvent(
        id=EVENT_ID,
        type="payment.succeeded",
        created_at=datetime.now(UTC),
        data=PaymentData(
            order_id=ORDER_ID,
            payment_id="pay_01J8EXAMPLE",
            amount=Decimal("129.90"),
            currency="BRL",
        ),
    )


@pytest.fixture
def producer_mock(monkeypatch):
    mock = Mock()
    mock.send.return_value.get.return_value = 0
    monkeypatch.setattr("app.payments.webhooks.producer", mock)
    return mock


@pytest_asyncio.fixture
async def order(db):
    order = Order(
        id=ORDER_ID,
        total_amount=Decimal("129.90"),
        currency="BRL",
        status=OrderStatus.PENDING,
    )
    db.add(order)
    await db.commit()
    return order


@pytest_asyncio.fixture
async def paid_order(order, db):
    order.status = OrderStatus.PAID
    await db.commit()
    return order


@pytest_asyncio.fixture
async def cancelled_order(order, db):
    order.status = OrderStatus.CANCELLED
    await db.commit()
    return order


@pytest_asyncio.fixture
async def stored_webhook_event(db, payment_event):
    event = WebhookEvent(
        provider_event_id=payment_event.id,
        event_type=payment_event.type,
        payload=payment_event.model_dump(mode="json"),
        received_at=datetime.now(UTC),
    )
    db.add(event)
    await db.commit()
    return event
