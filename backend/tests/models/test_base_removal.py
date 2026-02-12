"""
Tests to verify the removal of app.models.base and ensure system stability.
This confirms the "Pragmatic Architect" decision: 'Si c'est inutile, ça dégage'.
"""

import pytest
import sys
from sqlmodel import SQLModel


def test_base_module_is_gone():
    """Ensure app.models.base no longer exists."""
    with pytest.raises(ImportError):
        import app.models.base


def test_sqlmodel_metadata_registry():
    """Ensure SQLModel metadata correctly registers models without Base."""
    # Import a few models to trigger registration
    from app.models.user import User
    from app.models.assistant import Assistant

    # Check if tables are registered in SQLModel.metadata
    tables = SQLModel.metadata.tables.keys()
    assert "users" in tables
    assert "assistants" in tables


def test_alembic_env_updated():
    """Ensure alembic/env.py does not import the deleted base module."""
    import os

    # Locate alembic/env.py relative to this test file
    # This approaches from backend/tests/models -> backend/alembic
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    env_path = os.path.join(base_dir, "alembic", "env.py")

    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            content = f.read()
            assert (
                "from app.models.base import Base" not in content
            ), "alembic/env.py should not import Base from app.models.base"
            assert (
                "target_metadata = SQLModel.metadata" in content or "target_metadata = Base.metadata" not in content
            ), "alembic/env.py should use SQLModel.metadata"
