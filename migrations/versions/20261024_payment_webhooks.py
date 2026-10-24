import sqlalchemy as sa
from alembic import op


def upgrade():
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "provider_event_id",
            sa.String(length=128),
            nullable=False,
            unique=True,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "order_id",
            sa.UUID(),
            sa.ForeignKey("orders.id"),
            nullable=False,
        ),
        sa.Column("provider_payment_id", sa.String(length=128), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_index(
        "ix_ledger_provider_payment",
        "ledger_entries",
        ["provider_payment_id"],
    )

    op.add_column(
        "orders",
        sa.Column("provider_payment_id", sa.String(length=128), nullable=True),
    )
    op.add_column("orders", sa.Column("paid_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("orders", "paid_at")
    op.drop_column("orders", "provider_payment_id")
    op.drop_index("ix_ledger_provider_payment")
    op.drop_table("ledger_entries")
    op.drop_table("webhook_events")
