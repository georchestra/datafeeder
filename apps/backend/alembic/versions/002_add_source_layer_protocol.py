"""add source_layer and source_protocol to integrity_link

Revision ID: 002
Revises: 001
Create Date: 2026-04-23

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "integrity_link",
        sa.Column("source_layer", sa.String(256), nullable=True),
        schema="datafeeder",
    )
    op.add_column(
        "integrity_link",
        sa.Column("source_protocol", sa.String(32), nullable=True),
        schema="datafeeder",
    )


def downgrade() -> None:
    op.drop_column("integrity_link", "source_protocol", schema="datafeeder")
    op.drop_column("integrity_link", "source_layer", schema="datafeeder")
