"""drop_unused_knowledge_tables

Revision ID: 6720795de228
Revises: 0083dbd5d1f2
Create Date: 2026-02-17 21:10:45.499323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6720795de228'
down_revision: Union[str, Sequence[str], None] = '0083dbd5d1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Drop knowledge_documents first because it depends on knowledge_bases (FK)
    # Check if table exists before dropping to be safe (though Alembic usually assumes state)
    # We use IF EXISTS for raw SQL or just try/except blocks in python, but standard alembic
    # op.drop_table doesn't have if_exists=True until very recent versions or via specialized dialects.
    # However, since we know they were created in ac5e71ba4874, we can drop them.
    
    # Drop knowledge_documents
    op.drop_table('knowledge_documents')
    
    # Drop knowledge_bases
    op.drop_table('knowledge_bases')


def downgrade() -> None:
    """Downgrade schema."""
    # Re-create tables if we roll back (restoring state from ac5e71ba4874)
    # Import postgresql dialect for JSONB
    from sqlalchemy.dialects import postgresql
    
    op.create_table('knowledge_bases',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('connector_type', sa.String(), nullable=False),
        sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=True),
        sa.Column('schedule_cron', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('knowledge_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('knowledge_base_id', sa.UUID(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_name', sa.String(), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=True),
        sa.Column('last_modified_at_source', sa.DateTime(timezone=True), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('file_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('knowledge_base_id', 'file_path', name='uq_kb_file_path')
    )
    
    op.create_index(op.f('ix_knowledge_documents_knowledge_base_id'), 'knowledge_documents', ['knowledge_base_id'], unique=False)
