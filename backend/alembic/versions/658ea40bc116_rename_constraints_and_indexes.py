"""rename_constraints_and_indexes

Revision ID: 658ea40bc116
Revises: 976cd9ffd628
Create Date: 2025-12-08 14:06:29.060101

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '658ea40bc116'
down_revision: Union[str, Sequence[str], None] = '976cd9ffd628'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename Primary Key for connectors
    op.execute('ALTER TABLE connectors RENAME CONSTRAINT "knowledge_bases_pkey" TO "connectors_pkey"')

    # Rename Primary Key for connectors_documents
    op.execute('ALTER TABLE connectors_documents RENAME CONSTRAINT "knowledge_documents_pkey" TO "connectors_documents_pkey"')

    # Rename Index for connectors_documents
    op.execute('ALTER INDEX "ix_knowledge_documents_knowledge_base_id" RENAME TO "ix_connectors_documents_connector_id"')

    # Rename Foreign Key (if it has a legacy name - verifying assumption or just trying safe rename if exists)
    # Based on user image, FK is "fk_connectors_documents_connector_id" which seems correct already?
    # User image shows "fk_connectors_documents_connector_id".
    # Wait, if tables were renamed, usually FK constraints might keep old names unless explicitly renamed?
    # But user image shows FK name is correct.
    # The image shows "knowledge_bases_pkey", "knowledge_documents_pkey", "ix_knowledge_documents_knowledge_base_id".
    # So I only target those.


def downgrade() -> None:
    """Downgrade schema."""
    # Revert Index Rename
    op.execute('ALTER INDEX "ix_connectors_documents_connector_id" RENAME TO "ix_knowledge_documents_knowledge_base_id"')

    # Revert PK Rename for connectors_documents
    op.execute('ALTER TABLE connectors_documents RENAME CONSTRAINT "connectors_documents_pkey" TO "knowledge_documents_pkey"')

    # Revert PK Rename for connectors
    op.execute('ALTER TABLE connectors RENAME CONSTRAINT "connectors_pkey" TO "knowledge_bases_pkey"')
