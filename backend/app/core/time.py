from datetime import datetime, timezone


class TimeProvider:
    """Abstract time provider for dependency injection."""

    def utcnow(self) -> datetime:
        raise NotImplementedError


class SystemClock(TimeProvider):
    """Production clock using system time."""

    def utcnow(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock(TimeProvider):
    """Mock clock for testing with fixed time."""

    def __init__(self, fixed_time: datetime):
        self.fixed_time = fixed_time

    def utcnow(self) -> datetime:
        return self.fixed_time

    def set_time(self, new_time: datetime) -> None:
        """Update the fixed time."""
        self.fixed_time = new_time
