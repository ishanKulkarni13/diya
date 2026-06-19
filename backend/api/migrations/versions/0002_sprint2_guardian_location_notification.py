"""add sprint2 guardian location notification tables

Revision ID: a7f8e9d12345
Revises: 4570c0c285e8
Create Date: 2026-06-19 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7f8e9d12345"
down_revision: Union[str, Sequence[str], None] = "4570c0c285e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Sprint 2 tables and phone_number to users."""

    # ── Add phone_number to users ────────────────────────────────────
    op.add_column("users", sa.Column("phone_number", sa.String(length=20), nullable=True))

    # ── guardian_relationships ───────────────────────────────────────
    op.create_table(
        "guardian_relationships",
        sa.Column("blind_user_id", sa.Uuid(), nullable=False),
        sa.Column("guardian_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_guardian_relationships")),
        sa.UniqueConstraint("blind_user_id", "guardian_user_id", name="uq_guardian_relationship"),
    )
    op.create_index(
        op.f("ix_guardian_relationships_blind_user_id"),
        "guardian_relationships",
        ["blind_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_guardian_relationships_guardian_user_id"),
        "guardian_relationships",
        ["guardian_user_id"],
        unique=False,
    )

    # ── guardian_invites ──────────────────────────────────────────────
    op.create_table(
        "guardian_invites",
        sa.Column("blind_user_id", sa.Uuid(), nullable=False),
        sa.Column("guardian_email", sa.String(length=255), nullable=False),
        sa.Column("relationship_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_guardian_invites")),
    )
    op.create_index(
        op.f("ix_guardian_invites_blind_user_id"),
        "guardian_invites",
        ["blind_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_guardian_invites_guardian_email"),
        "guardian_invites",
        ["guardian_email"],
        unique=False,
    )

    # ── current_locations ─────────────────────────────────────────────
    op.create_table(
        "current_locations",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_current_locations")),
        sa.UniqueConstraint("user_id", name="uq_current_location_user"),
    )
    op.create_index(
        op.f("ix_current_locations_user_id"),
        "current_locations",
        ["user_id"],
        unique=True,
    )

    # ── device_tokens ─────────────────────────────────────────────────
    op.create_table(
        "device_tokens",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(length=512), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_device_tokens")),
        sa.UniqueConstraint("user_id", "token", name="uq_device_token"),
    )
    op.create_index(
        op.f("ix_device_tokens_token"),
        "device_tokens",
        ["token"],
        unique=True,
    )
    op.create_index(
        op.f("ix_device_tokens_user_id"),
        "device_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop Sprint 2 tables and phone_number from users."""

    op.drop_index(op.f("ix_device_tokens_user_id"), table_name="device_tokens")
    op.drop_index(op.f("ix_device_tokens_token"), table_name="device_tokens")
    op.drop_table("device_tokens")

    op.drop_index(op.f("ix_current_locations_user_id"), table_name="current_locations")
    op.drop_table("current_locations")

    op.drop_index(op.f("ix_guardian_invites_guardian_email"), table_name="guardian_invites")
    op.drop_index(op.f("ix_guardian_invites_blind_user_id"), table_name="guardian_invites")
    op.drop_table("guardian_invites")

    op.drop_index(
        op.f("ix_guardian_relationships_guardian_user_id"),
        table_name="guardian_relationships",
    )
    op.drop_index(
        op.f("ix_guardian_relationships_blind_user_id"),
        table_name="guardian_relationships",
    )
    op.drop_table("guardian_relationships")

    op.drop_column("users", "phone_number")
