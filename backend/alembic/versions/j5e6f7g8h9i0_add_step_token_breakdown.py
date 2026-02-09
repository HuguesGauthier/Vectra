"""add step_token_breakdown to usage_stats

Revision ID: j5e6f7g8h9i0
Revises: i4d5e6f7g8h9
Create Date: 2026-01-14 07:56:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'j5e6f7g8h9i0'
down_revision: Union[str, Sequence[str], None] = 'i4d5e6f7g8h9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add step_token_breakdown column to usage_stats table."""
    op.add_column('usage_stats', 
        sa.Column('step_token_breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Remove step_token_breakdown column from usage_stats table."""
    op.drop_column('usage_stats', 'step_token_breakdown')
