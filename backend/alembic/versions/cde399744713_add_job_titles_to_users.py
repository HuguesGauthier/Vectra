"""add job_titles to users

Revision ID: cde399744713
Revises: 8719d6449a75
Create Date: 2026-02-21 20:19:57.522489

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cde399744713'
down_revision: Union[str, Sequence[str], None] = '8719d6449a75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add job_titles as a JSON column to the users table
    op.add_column("users", sa.Column("job_titles", sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "job_titles")
