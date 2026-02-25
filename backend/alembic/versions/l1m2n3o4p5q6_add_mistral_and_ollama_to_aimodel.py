"""add_mistral_and_ollama_to_aimodel

Revision ID: l1m2n3o4p5q6
Revises: k6f7g8h9i0j1
Create Date: 2026-02-06 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'l1m2n3o4p5q6' # Arbitrary unique ID
down_revision: Union[str, None] = 'f9cb844ef13c' # Previous revision is now the user_id addition
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use direct SQL to alter the enum type as Postgres doesn't support generic ALTER TYPE easily via SA
    # For PostgreSQL 9.1+ we can use ALTER TYPE ... ADD VALUE
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE aimodel ADD VALUE IF NOT EXISTS 'mistral'")
        op.execute("ALTER TYPE aimodel ADD VALUE IF NOT EXISTS 'ollama'")


def downgrade() -> None:
    # Downgrading enum values in Postgres is hard (requires creating new type, migrating data, dropping old type).
    # Usually we skip strict downgrade for enum addition or just leave them.
    pass
