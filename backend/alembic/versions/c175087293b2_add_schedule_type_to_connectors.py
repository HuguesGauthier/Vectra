"""add_schedule_type_to_connectors

Revision ID: c175087293b2
Revises: bc14de6ecb97
Create Date: 2025-12-15 11:48:52.291496

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c175087293b2'
down_revision: Union[str, Sequence[str], None] = 'bc14de6ecb97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('connectors', sa.Column('schedule_type', sa.String(), nullable=True, server_default='manual'))


def downgrade() -> None:
    op.drop_column('connectors', 'schedule_type')
