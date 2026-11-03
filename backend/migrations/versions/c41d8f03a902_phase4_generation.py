"""4단계 권한 검증·영속 생성 큐.

Revision ID: c41d8f03a902
Revises: b34a9c12d701
"""

import sqlalchemy as sa
from alembic import op

revision = "c41d8f03a902"
down_revision = "b34a9c12d701"
branch_labels = None
depends_on = None


def upgrade():
    for name, length, default in (
        ("photo_rights_status", 20, "unverified"),
        ("detailed_rights_status", 20, "unverified"),
        ("output_rights_status", 20, "unverified"),
        ("generation_status", 20, "idle"),
    ):
        op.add_column(
            "garments", sa.Column(name, sa.String(length), nullable=False, server_default=default)
        )
    op.add_column(
        "garments", sa.Column("rights_version", sa.Integer(), nullable=False, server_default="1")
    )
    for name, length in (
        ("generation_job_id", 36),
        ("model_format", 10),
        ("model_version", 40),
        ("generation_error", 100),
        ("updated_at", 40),
    ):
        op.add_column("garments", sa.Column(name, sa.String(length), nullable=True))
    op.add_column(
        "reports", sa.Column("kind", sa.String(20), nullable=False, server_default="rights")
    )
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "garment_id",
            sa.String(36),
            sa.ForeignKey("garments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("stage", sa.String(30), nullable=False),
        sa.Column("mode", sa.String(1), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("result_metadata", sa.JSON(), nullable=True),
        sa.Column("rights_version", sa.Integer(), nullable=False),
        sa.Column("garment_revision", sa.Integer(), nullable=False),
        sa.Column("lease_until", sa.Float(), nullable=True),
        sa.Column("claim_token", sa.String(36), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_generation_jobs_garment_id", "generation_jobs", ["garment_id"])
    op.create_index("ix_generation_jobs_status", "generation_jobs", ["status"])
    op.create_table(
        "rights_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "garment_id",
            sa.String(36),
            sa.ForeignKey("garments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("mime", sa.String(30), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_rights_evidence_garment_id", "rights_evidence", ["garment_id"])
    op.create_table(
        "rights_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "garment_id",
            sa.String(36),
            sa.ForeignKey("garments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_id", sa.String(36), nullable=True),
        sa.Column("decision", sa.JSON(), nullable=False),
        sa.Column("notes", sa.String(2000), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_rights_reviews_garment_id", "rights_reviews", ["garment_id"])


def downgrade():
    for table in ("rights_reviews", "rights_evidence", "generation_jobs"):
        op.drop_table(table)
    with op.batch_alter_table("reports") as batch:
        batch.drop_column("kind")
    with op.batch_alter_table("garments") as batch:
        for name in (
            "photo_rights_status",
            "detailed_rights_status",
            "output_rights_status",
            "rights_version",
            "generation_status",
            "generation_job_id",
            "model_format",
            "model_version",
            "generation_error",
            "updated_at",
        ):
            batch.drop_column(name)
