"""rename_tables

Revision ID: 976cd9ffd628
Revises: 1afea1289538
Create Date: 2025-12-08 11:57:01.307730

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '976cd9ffd628'
down_revision: Union[str, Sequence[str], None] = '1afea1289538'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename tables
    op.rename_table('knowledge_bases', 'connectors')
    op.rename_table('knowledge_documents', 'connectors_documents')
    op.rename_table('assistant_knowledge_bases', 'assistant_connectors')

    # 2. Rename columns (knowledge_base_id -> connector_id)
    # Note: We use execute for safer column/constraint renaming if specific dialect support is needed, 
    # but alter_column with new_column_name is clean in newer Alembic.
    op.alter_column('connectors_documents', 'knowledge_base_id', new_column_name='connector_id')
    op.alter_column('assistant_connectors', 'knowledge_base_id', new_column_name='connector_id')
    
    # 3. Fix Constraints names (Optional but clean)
    # Constraints like FKs might still have old names or simply point to 'connectors' now.
    # Postgres usually updates FK references on table rename automatically.
    # But renaming the column might break default FK constraints if not handled.
    # We'll trust PG to handle the pointer updates, but we should ensure the FK exists.
    # Since we renamed the table and column, the FK logic should hold if purely structural.
    # However, to be 100% sure we match the code definition:
    
    # Re-create FK on connectors_documents.connector_id -> connectors.id
    # We first drop the old constraint if we can guess its name, or just let it be if it works.
    # Safer approach: Explicitly drop and recreate FKs to properly name them.
    # Constraint names are usually `knowledge_documents_knowledge_base_id_fkey` or similar.
    
    # Attempt to drop old constraint on connectors_documents
    try:
        op.drop_constraint('knowledge_documents_knowledge_base_id_fkey', 'connectors_documents', type_='foreignkey')
    except Exception:
        pass # Ignore if not exists or named differently
        
    op.create_foreign_key(
        'fk_connectors_documents_connector_id',
        'connectors_documents', 'connectors',
        ['connector_id'], ['id']
    )
    
    # Attempt to drop old constraint on assistant_connectors
    try:
        op.drop_constraint('assistant_knowledge_bases_knowledge_base_id_fkey', 'assistant_connectors', type_='foreignkey')
        op.drop_constraint('assistant_knowledge_bases_assistant_id_fkey', 'assistant_connectors', type_='foreignkey')
    except Exception:
        pass

    op.create_foreign_key(
        'fk_assistant_connectors_connector_id',
        'assistant_connectors', 'connectors',
        ['connector_id'], ['id']
    )
    op.create_foreign_key(
        'fk_assistant_connectors_assistant_id',
        'assistant_connectors', 'assistants',
        ['assistant_id'], ['id']
    )

    # Rename Unique Constraint on connectors_documents
    # uq_kb_file_path -> uq_connector_file_path
    try:
        op.drop_constraint('uq_kb_file_path', 'connectors_documents', type_='unique')
    except Exception:
        pass
    op.create_unique_constraint('uq_connector_file_path', 'connectors_documents', ['connector_id', 'file_path'])


def downgrade() -> None:
    # Reverse operations
    
    # Rename columns back
    op.alter_column('connectors_documents', 'connector_id', new_column_name='knowledge_base_id')
    op.alter_column('assistant_connectors', 'connector_id', new_column_name='knowledge_base_id')

    # Rename tables back
    op.rename_table('assistant_connectors', 'assistant_knowledge_bases')
    op.rename_table('connectors_documents', 'knowledge_documents')
    op.rename_table('connectors', 'knowledge_bases')
