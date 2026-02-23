"""add_default_to_updated_at_in_connectors_documents

Revision ID: 61ac41c83a99
Revises: bf8d3ecfe541
Create Date: 2026-02-13 07:57:53.332730

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "61ac41c83a99"
down_revision: Union[str, Sequence[str], None] = "bf8d3ecfe541"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add DEFAULT NOW() to updated_at column in connectors_documents table
    op.execute("ALTER TABLE connectors_documents ALTER COLUMN updated_at SET DEFAULT NOW()")


def downgrade() -> None:
    """Downgrade schema."""
    # Remove DEFAULT from updated_at column
    op.execute("ALTER TABLE connectors_documents ALTER COLUMN updated_at DROP DEFAULT")
