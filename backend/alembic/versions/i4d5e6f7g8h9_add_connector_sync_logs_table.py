"""add connector sync logs table

Revision ID: i4d5e6f7g8h9
Revises: h3c4d5e6f7g8
Create Date: 2026-01-13 20:06:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'i4d5e6f7g8h9'
down_revision: Union[str, None] = 'h3c4d5e6f7g8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create connector_sync_logs table
    op.create_table(
        'connector_sync_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('connector_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('documents_synced', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sync_duration', sa.Float(), nullable=True),
        sa.Column('sync_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['connector_id'], ['connectors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_connector_sync_logs_connector_id', 'connector_sync_logs', ['connector_id'])
    op.create_index('ix_connector_sync_logs_sync_time', 'connector_sync_logs', ['sync_time'])
    op.create_index('ix_connector_sync_logs_connector_time', 'connector_sync_logs', ['connector_id', 'sync_time'])
    op.create_index('ix_connector_sync_logs_status_time', 'connector_sync_logs', ['status', 'sync_time'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_connector_sync_logs_status_time', table_name='connector_sync_logs')
    op.drop_index('ix_connector_sync_logs_connector_time', table_name='connector_sync_logs')
    op.drop_index('ix_connector_sync_logs_sync_time', table_name='connector_sync_logs')
    op.drop_index('ix_connector_sync_logs_connector_id', table_name='connector_sync_logs')
    
    # Drop table
    op.drop_table('connector_sync_logs')
