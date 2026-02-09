"""add_progress_tracking_columns

Revision ID: e5d36cca9d2b
Revises: c175087293b2
Create Date: 2025-12-16 13:32:05.053942

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e5d36cca9d2b'
down_revision: Union[str, Sequence[str], None] = 'c175087293b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('connectors_documents', sa.Column('chunks_total', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('connectors_documents', sa.Column('chunks_processed', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('connectors_documents', 'chunks_processed')
    op.drop_column('connectors_documents', 'chunks_total')
