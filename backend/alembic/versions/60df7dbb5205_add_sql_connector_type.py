"""add_sql_connector_type

Revision ID: 60df7dbb5205
Revises: 7d08b7230504
Create Date: 2026-01-20 08:44:15.529955

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '60df7dbb5205'
down_revision: Union[str, Sequence[str], None] = '7d08b7230504'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add 'sql' value to the connectortype enum
    op.execute("ALTER TYPE connectortype ADD VALUE IF NOT EXISTS 'sql'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL does not support removing enum values directly
    # If downgrade is needed, the enum would need to be recreated
    # For safety, we'll leave this as a no-op warning
    print("WARNING: Cannot remove 'sql' from connectortype enum. Manual intervention required if needed.")
    pass
