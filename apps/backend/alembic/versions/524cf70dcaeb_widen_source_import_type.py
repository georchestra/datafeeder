"""widen integrity_link.source_import_type for the direct_access import type

Revision ID: 524cf70dcaeb
Revises: 311bbeb94ed3
Create Date: 2026-11-02

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "524cf70dcaeb"
down_revision: str | None = "311bbeb94ed3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # varchar(10) fitted the longest value of the time ('prefilled'), not 'direct_access'
    op.execute(
        "ALTER TABLE IF EXISTS datafeeder.integrity_link "
        "ALTER COLUMN source_import_type TYPE varchar(32)"
    )


def downgrade() -> None:
    # Fails while direct_access integrity links remain
    op.execute(
        "ALTER TABLE IF EXISTS datafeeder.integrity_link "
        "ALTER COLUMN source_import_type TYPE varchar(10)"
    )
