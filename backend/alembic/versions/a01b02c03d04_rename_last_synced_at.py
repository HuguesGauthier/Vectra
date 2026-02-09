"""rename last_synced_at to last_vectorized_at

Revision ID: a01b02c03d04
Revises: 510ce9e60d39
Create Date: 2025-12-23 13:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a01b02c03d04'
down_revision: Union[str, Sequence[str], None] = '65f8c02651c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('connectors', 'last_synced_at', new_column_name='last_vectorized_at')


def downgrade() -> None:
    op.alter_column('connectors', 'last_vectorized_at', new_column_name='last_synced_at')
