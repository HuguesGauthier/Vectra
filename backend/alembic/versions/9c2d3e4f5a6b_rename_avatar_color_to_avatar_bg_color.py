"""rename avatar_color to avatar_bg_color

Revision ID: 9c2d3e4f5a6b
Revises: 03f2eef5eadd
Create Date: 2026-01-09 13:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9c2d3e4f5a6b'
down_revision: Union[str, None] = '198405d6ca2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename the column avatar_color to avatar_bg_color in assistants table
    op.alter_column('assistants', 'avatar_color', new_column_name='avatar_bg_color')


def downgrade() -> None:
    # Revert the column rename
    op.alter_column('assistants', 'avatar_bg_color', new_column_name='avatar_color')
