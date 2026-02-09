import json

import pytest

from app.services.chat.utils import EventFormatter


class NON_SERIALIZABLE_OBJ:
    pass


def test_event_formatter_robustness():
    """Test that EventFormatter handles non-serializable payloads gracefully."""

    # Arrange
    obj = NON_SERIALIZABLE_OBJ()

    # Act
    # This would crash without default=str
    result = EventFormatter.format("test_step", "completed", "en", payload={"data": obj}, duration=0.1)

    # Assert
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert parsed["label"] == "test_step_completed"
    # The non-serializable object should be converted to its string representation
    assert "NON_SERIALIZABLE_OBJ" in str(parsed["payload"]["data"])
