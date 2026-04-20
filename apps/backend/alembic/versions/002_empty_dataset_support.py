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
    # Allow staging_table_name to be NULL (empty datasets have no staging table)
    op.alter_column("integrity_link", "staging_table_name", nullable=True)

    # Add 'empty' value to the source_import_type enum
    # ADD VALUE cannot run inside a transaction, so we use COMMIT trick via execute_if
    op.execute("ALTER TYPE source_import_type ADD VALUE IF NOT EXISTS 'empty'")


def downgrade() -> None:
    # Restore NOT NULL constraint (will fail if any row has NULL staging_table_name)
    op.alter_column("integrity_link", "staging_table_name", nullable=False)

    # PostgreSQL does not support removing enum values; downgrade is a no-op for the enum
