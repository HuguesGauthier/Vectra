"""Refactor Connector Domain

Revision ID: ce6c6ed7d4bf
Revises: ac5e71ba4874
Create Date: 2025-12-13 20:49:32.660576

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ce6c6ed7d4bf'
down_revision: Union[str, Sequence[str], None] = 'ac5e71ba4874'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('connectors', sa.Column('total_docs_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('connectors', sa.Column('indexed_docs_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('connectors', sa.Column('failed_docs_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('connectors', sa.Column('last_sync_start_at', sa.DateTime(), nullable=True))
    op.add_column('connectors', sa.Column('last_sync_end_at', sa.DateTime(), nullable=True))
    op.add_column('connectors_documents', sa.Column('doc_token_count', sa.Integer(), nullable=True))
    op.add_column('connectors_documents', sa.Column('vector_point_count', sa.Integer(), nullable=True))
    op.add_column('connectors_documents', sa.Column('processing_duration_ms', sa.Integer(), nullable=True))
    op.add_column('connectors_documents', sa.Column('mime_type', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('connectors_documents', 'mime_type')
    op.drop_column('connectors_documents', 'processing_duration_ms')
    op.drop_column('connectors_documents', 'vector_point_count')
    op.drop_column('connectors_documents', 'doc_token_count')
    op.drop_column('connectors', 'last_sync_end_at')
    op.drop_column('connectors', 'last_sync_start_at')
    op.drop_column('connectors', 'failed_docs_count')
    op.drop_column('connectors', 'indexed_docs_count')
    op.drop_column('connectors', 'total_docs_count')
