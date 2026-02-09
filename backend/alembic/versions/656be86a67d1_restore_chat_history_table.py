"""Restore chat_history table

Revision ID: 656be86a67d1
Revises: ce6c6ed7d4bf
Create Date: 2025-12-13 20:52:12.335550

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '656be86a67d1'
down_revision: Union[str, Sequence[str], None] = 'ce6c6ed7d4bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('chat_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key', name=op.f('chat_history:unique_key'))
    )
    op.create_index(op.f('chat_history:idx_key'), 'chat_history', ['key'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('chat_history:idx_key'), table_name='chat_history')
    op.drop_table('chat_history')
