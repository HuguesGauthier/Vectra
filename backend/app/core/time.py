from datetime import datetime, timezone


class TimeProvider:
    """Abstract time provider for dependency injection."""

    def utcnow(self) -> datetime:
        raise NotImplementedError


class SystemClock(TimeProvider):
    """Production clock using system time."""

    def utcnow(self) -> datetime:
        return datetime.now(timezone.utc)
