"""add_vanna_sql_connector_type

Revision ID: k6f7g8h9i0j1
Revises: j5e6f7g8h9i0
Create Date: 2026-02-03 14:05:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'k6f7g8h9i0j1'
down_revision: Union[str, Sequence[str], None] = '60df7dbb5205'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add 'vanna_sql' value to the connectortype enum
    op.execute("ALTER TYPE connectortype ADD VALUE IF NOT EXISTS 'vanna_sql'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL does not support removing enum values directly
    # If downgrade is needed, the enum would need to be recreated
    # For safety, we'll leave this as a no-op warning
    print("WARNING: Cannot remove 'vanna_sql' from connectortype enum. Manual intervention required if needed.")
    pass
