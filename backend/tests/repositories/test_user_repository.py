"""
Tests for UserRepository.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import TechnicalError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdate


@pytest.fixture
def mock_db():
    mock = AsyncMock()
    mock.add = MagicMock()
    return mock


@pytest.fixture
def repository(mock_db):
    return UserRepository(mock_db)


@pytest.mark.asyncio
async def test_get_by_email_success(repository, mock_db):
    # Arrange
    email = "test@example.com"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = User(email=email, hashed_password="pwd", is_active=True)
    mock_db.execute.return_value = mock_result

    # Act
    user = await repository.get_by_email(email)

    # Assert
    assert user.email == email


@pytest.mark.asyncio
async def test_get_by_email_failure(repository, mock_db):
    # Arrange
    mock_db.execute.side_effect = SQLAlchemyError("DB connection lost")

    # Act & Assert
    with pytest.raises(TechnicalError):
        await repository.get_by_email("test@example.com")


@pytest.mark.asyncio
async def test_deactivate_user_uses_schema(repository, mock_db):
    # Arrange
    uid = uuid4()
    # Mock update internal steps (get_by_id then commit)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = User(id=uid, hashed_password="x")
    mock_db.execute.return_value = mock_result

    # Act
    await repository.deactivate_user(uid)

    # Assert
    # Verify add() was called with user having is_active=False
    assert mock_db.add.called
    saved_user = mock_db.add.call_args[0][0]
    assert saved_user.is_active is False
