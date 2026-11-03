"""GLB 워커 응답과 민감 정보 없는 실패 단계 기록."""

import sqlalchemy as sa
from alembic import op

revision = "f71a4c9d1105"
down_revision = "e61f3b8c1004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("generation_jobs", sa.Column("failure_stage", sa.String(30), nullable=True))
    op.add_column("generation_jobs", sa.Column("exception_type", sa.String(80), nullable=True))
    op.create_table(
        "generation_workers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engine_version", sa.String(40), nullable=False),
        sa.Column("last_seen", sa.Float(), nullable=False),
    )
    op.create_index("ix_generation_workers_last_seen", "generation_workers", ["last_seen"])


def downgrade():
    op.drop_table("generation_workers")
    op.drop_column("generation_jobs", "exception_type")
    op.drop_column("generation_jobs", "failure_stage")
