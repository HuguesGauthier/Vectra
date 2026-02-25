"""remove reranker_provider

Revision ID: h3c4d5e6f7g8
Revises: g2b3c4d5e6f7
Create Date: 2026-01-13 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'h3c4d5e6f7g8'
down_revision: Union[str, None] = 'g2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop the column
    op.drop_column('assistants', 'reranker_provider')
    
    # 2. Drop the Enum type explicitly (Postgres doesn't auto-drop enums)
    # We use execute because alembic helpers for enum dropping are tricky across versions
    op.execute("DROP TYPE IF EXISTS rerankerprovider")


def downgrade() -> None:
    # Re-create Enum
    op.execute("CREATE TYPE rerankerprovider AS ENUM ('cohere', 'jina', 'local')")
    
    # Re-add column
    op.add_column('assistants', sa.Column('reranker_provider', postgresql.ENUM('cohere', 'jina', 'local', name='rerankerprovider'), autoincrement=False, nullable=True))
