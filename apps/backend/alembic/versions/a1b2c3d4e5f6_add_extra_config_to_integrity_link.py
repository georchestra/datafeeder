"""add extra_config jsonb to integrity_link

Revision ID: a1b2c3d4e5f6
Revises: 311bbeb94ed3
Create Date: 2026-06-09

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "311bbeb94ed3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE datafeeder.integrity_link ADD COLUMN IF NOT EXISTS extra_config jsonb NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE datafeeder.integrity_link DROP COLUMN IF EXISTS extra_config")
