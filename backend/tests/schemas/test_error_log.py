from uuid import uuid4
from datetime import datetime
from app.schemas.error_log import ErrorLogResponse


def test_error_log_response_schema():
    """Verify ErrorLogResponse schema can be instantiated."""
    log_id = uuid4()
    now = datetime.now()

    response = ErrorLogResponse(
        id=log_id, timestamp=now, status_code=200, method="GET", path="/api/test", error_message="OK"
    )

    assert response.id == log_id
    assert response.status_code == 200
    assert response.method == "GET"
    # Ensure excluded fields logic (if any) is respected effectively by Pydantic
    # (Here we just check basic instantiation)
