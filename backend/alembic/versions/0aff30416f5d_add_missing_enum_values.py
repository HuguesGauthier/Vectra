"""add_missing_enum_values

Revision ID: 0aff30416f5d
Revises: b97a4bc14bb6
Create Date: 2026-01-11 18:58:32.416912

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0aff30416f5d'
down_revision: Union[str, Sequence[str], None] = 'b97a4bc14bb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add missing values to aimodel enum
    op.execute("ALTER TYPE aimodel ADD VALUE IF NOT EXISTS 'gemini'")
    op.execute("ALTER TYPE aimodel ADD VALUE IF NOT EXISTS 'openai'")
    
    # Add missing value to rerankerprovider enum
    op.execute("ALTER TYPE rerankerprovider ADD VALUE IF NOT EXISTS 'local'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL doesn't support removing enum values directly
    # You would need to drop and recreate the enum type, which is complex
    # For now, we'll leave this as a no-op
    pass
