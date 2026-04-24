"""replace final_table_name unique with org_table composite unique

Revision ID: 12856770e05b
Revises: 002
Create Date: 2026-04-24 17:15:26.616936

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "12856770e05b"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "integrity_link_final_table_name_key",
        "integrity_link",
        schema="datafeeder",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_integrity_link_org_final_table",
        "integrity_link",
        ["integrity_organization", "final_table_name"],
        schema="datafeeder",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_integrity_link_org_final_table",
        "integrity_link",
        schema="datafeeder",
        type_="unique",
    )
    op.create_unique_constraint(
        "integrity_link_final_table_name_key",
        "integrity_link",
        ["final_table_name"],
        schema="datafeeder",
    )
