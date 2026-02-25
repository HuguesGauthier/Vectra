"""add_configuration_column_to_connector_documents

Revision ID: 510ce9e60d39
Revises: e5d36cca9d2b
Create Date: 2025-12-17 11:33:04.919786

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '510ce9e60d39'
down_revision: Union[str, Sequence[str], None] = 'e5d36cca9d2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add configuration column to connectors_documents table
    op.add_column(
        'connectors_documents',
        sa.Column(
            'configuration',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'{}'::jsonb")
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove configuration column from connectors_documents table
    op.drop_column('connectors_documents', 'configuration')
