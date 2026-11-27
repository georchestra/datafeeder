"""add last_run_status to integrity links

Revision ID: 69fffa1efda8
Revises: baa07c1bb070
Create Date: 2026-11-23

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "69fffa1efda8"
down_revision: str | None = "baa07c1bb070"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "integrity_link",
        sa.Column("last_run_status", sa.String(length=16), nullable=True),
        schema="datafeeder",
    )
    # Datasets already ingested
    op.execute(
        "UPDATE datafeeder.integrity_link SET last_run_status = 'success' "
        "WHERE last_retrieval_timestamp IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("integrity_link", "last_run_status", schema="datafeeder")
