"""6단계 비공개 취향·추천·피드백. 기존 테이블과 데이터를 유지한다."""

import sqlalchemy as sa
from alembic import op

revision = "e61f3b8c1004"
down_revision = "d51e2a7b0903"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "style_preferences",
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
    )
    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("slots", sa.JSON(), nullable=False),
        sa.Column("model_refs", sa.JSON(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "mannequin_id",
            sa.String(36),
            sa.ForeignKey("saved_mannequins.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("feedback", sa.String(12), nullable=False),
        sa.Column("feedback_at", sa.String(40), nullable=True),
        sa.Column("saved_at", sa.String(40), nullable=True),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_recommendations_user_id", "recommendations", ["user_id"])


def downgrade():
    op.drop_table("recommendations")
    op.drop_table("style_preferences")
