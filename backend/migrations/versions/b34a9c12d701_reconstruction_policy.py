"""의류 복원 모드·권한·원본 보관 정책 추가.

Revision ID: b34a9c12d701
Revises: 75730b3d1871
"""

import sqlalchemy as sa
from alembic import op

revision = "b34a9c12d701"
down_revision = "75730b3d1871"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """기존 저장 동의는 보존하되 복원 권한을 승인으로 간주하지 않는다."""
    for name, length, default in (
        ("reconstruction_mode", 1, "A"),
        ("source_type", 20, "other"),
        ("rights_status", 20, "unverified"),
        ("original_image_retention", 20, "temporary"),
        ("model_visibility", 20, "private"),
    ):
        op.add_column(
            "garments", sa.Column(name, sa.String(length), nullable=False, server_default=default)
        )
    for name, length in (
        ("license_reference", 1000),
        ("generated_model_path", 500),
        ("rights_reviewed_at", 40),
    ):
        op.add_column("garments", sa.Column(name, sa.String(length), nullable=True))
    op.execute("UPDATE garments SET original_image_retention = 'consented_storage'")


def downgrade() -> None:
    """추가한 메타데이터만 제거한다."""
    with op.batch_alter_table("garments") as batch:
        for name in (
            "rights_reviewed_at",
            "generated_model_path",
            "license_reference",
            "model_visibility",
            "original_image_retention",
            "rights_status",
            "source_type",
            "reconstruction_mode",
        ):
            batch.drop_column(name)
