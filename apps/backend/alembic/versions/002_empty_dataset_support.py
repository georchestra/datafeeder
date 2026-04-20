"""empty dataset support: nullable staging_table_name + EMPTY import type

Revision ID: 002
Revises: 001
Create Date: 2026-04-20

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Allow staging_table_name to be NULL (empty datasets have no staging table).
    # source_import_type is a varchar — no enum ALTER needed, 'empty' is accepted as-is.
    op.execute(
        "ALTER TABLE IF EXISTS datafeeder.integrity_link ALTER COLUMN staging_table_name DROP NOT NULL"
    )


def downgrade() -> None:
    # Restore NOT NULL constraint (will fail if any row has NULL staging_table_name)
    op.execute(
        "ALTER TABLE IF EXISTS datafeeder.integrity_link ALTER COLUMN staging_table_name SET NOT NULL"
    )
