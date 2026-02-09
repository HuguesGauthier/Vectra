"""rename_user_to_users

Revision ID: 79e451b98cf0
Revises: a2db2b18a9a2
Create Date: 2026-01-05 13:49:14.417207

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '79e451b98cf0'
down_revision: Union[str, Sequence[str], None] = 'a2db2b18a9a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table('user', 'users')


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table('users', 'user')
