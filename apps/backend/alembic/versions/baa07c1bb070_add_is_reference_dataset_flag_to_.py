"""add is_reference_dataset flag to integrity links

Revision ID: baa07c1bb070
Revises: 311bbeb94ed3
Create Date: 2026-10-23 12:57:59.557313

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "baa07c1bb070"
down_revision: str | None = "311bbeb94ed3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "integrity_link",
        sa.Column("is_reference_dataset", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="datafeeder",
    )


def downgrade() -> None:
    op.drop_column("integrity_link", "is_reference_dataset", schema="datafeeder")
