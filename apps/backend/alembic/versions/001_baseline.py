"""baseline

Revision ID: 001
Revises:
Create Date: 2026-04-13

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Schema already exists on all deployed instances.
    # New installations run alembic upgrade head after the SQL init scripts.
    pass


def downgrade() -> None:
    pass
