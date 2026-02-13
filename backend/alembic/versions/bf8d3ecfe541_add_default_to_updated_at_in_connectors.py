"""add_default_to_updated_at_in_connectors

Revision ID: bf8d3ecfe541
Revises: l1m2n3o4p5q6
Create Date: 2026-02-13 07:46:06.303159

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bf8d3ecfe541"
down_revision: Union[str, Sequence[str], None] = "l1m2n3o4p5q6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add DEFAULT NOW() to updated_at column in connectors table
    op.execute("ALTER TABLE connectors ALTER COLUMN updated_at SET DEFAULT NOW()")


def downgrade() -> None:
    """Downgrade schema."""
    # Remove DEFAULT from updated_at column
    op.execute("ALTER TABLE connectors ALTER COLUMN updated_at DROP DEFAULT")
