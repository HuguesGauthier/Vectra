from datetime import datetime, timezone, timedelta
import pytest
from app.core.time import SystemClock, FixedClock, TimeProvider


class TestTimeCore:
    def test_system_clock_now(self):
        """Happy Path: Verify SystemClock returns a valid UTC timezone-aware datetime."""
        clock = SystemClock()
        now = clock.utcnow()

        assert isinstance(now, datetime)
        assert now.tzinfo == timezone.utc

        # Verify it's actually "now" (within a small margin)
        real_now = datetime.now(timezone.utc)
        assert abs((now - real_now).total_seconds()) < 1.0

    def test_fixed_clock(self):
        """Happy Path: Verify FixedClock returns the configured time and can be updated."""
        fixed_dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed_dt)

        assert clock.utcnow() == fixed_dt

        # Update time
        new_dt = fixed_dt + timedelta(hours=1)
        clock.set_time(new_dt)
        assert clock.utcnow() == new_dt

    def test_time_provider_interface(self):
        """Worst Case: Verify TimeProvider abstract class raises NotImplementedError."""

        class IncompleteClock(TimeProvider):
            pass

        clock = IncompleteClock()
        with pytest.raises(NotImplementedError):
            clock.utcnow()
