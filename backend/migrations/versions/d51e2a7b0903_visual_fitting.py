"""5단계 비공개 마네킹 스냅샷·피팅·코디.

Revision ID: d51e2a7b0903
Revises: c41d8f03a902
"""

import sqlalchemy as sa
from alembic import op

revision = "d51e2a7b0903"
down_revision = "c41d8f03a902"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "saved_mannequins",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("profile", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_saved_mannequins_user_id", "saved_mannequins", ["user_id"])
    for name in ("fittings", "outfits"):
        columns = [
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "mannequin_id",
                sa.String(36),
                sa.ForeignKey("saved_mannequins.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("slots", sa.JSON(), nullable=False),
            sa.Column("adjustments", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.String(40), nullable=False),
        ]
        if name == "fittings":
            columns.extend(
                [
                    sa.Column("revision", sa.Integer(), nullable=False),
                    sa.Column("updated_at", sa.String(40), nullable=False),
                ]
            )
        else:
            columns.append(sa.Column("name", sa.String(80), nullable=False))
        op.create_table(name, *columns)
        op.create_index(f"ix_{name}_user_id", name, ["user_id"])


def downgrade():
    for name in ("outfits", "fittings", "saved_mannequins"):
        op.drop_table(name)
