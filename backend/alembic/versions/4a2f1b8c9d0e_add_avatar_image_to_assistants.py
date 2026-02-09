"""add avatar_image to assistants

Revision ID: 4a2f1b8c9d0e
Revises: 9c2d3e4f5a6b
Create Date: 2026-01-10 16:55:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4a2f1b8c9d0e'
down_revision: Union[str, None] = '9c2d3e4f5a6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add avatar_image column to assistants table
    op.add_column('assistants', sa.Column('avatar_image', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove avatar_image column from assistants table
    op.drop_column('assistants', 'avatar_image')
