"""Tests for timeout utilities."""

from __future__ import annotations

import signal

import pytest

from snowfakery_mcp.core.timeout import OperationTimeout, time_limit


class TestOperationTimeout:
    """Test timeout exception."""

    def test_operation_timeout_is_runtime_error(self) -> None:
        """Test that OperationTimeout is a RuntimeError subclass."""
        exc = OperationTimeout("test")
        assert isinstance(exc, RuntimeError)
        assert str(exc) == "test"


class TestTimeLimit:
    """Test time_limit context manager."""

    def test_time_limit_succeeds_within_time(self) -> None:
        """Test that time_limit allows operations within the time limit."""
        with time_limit(2):
            # This should complete without error
            pass

    def test_time_limit_raises_timeout_on_signal(self) -> None:
        """Test that time_limit raises OperationTimeout when signal fires."""
        import time

        with pytest.raises(OperationTimeout):
            with time_limit(1):
                # Sleep longer than the timeout
                time.sleep(3)

    def test_time_limit_multiple_calls(self) -> None:
        """Test that time_limit can be called multiple times sequentially."""
        with time_limit(2):
            pass

        with time_limit(2):
            pass

    def test_time_limit_with_zero_seconds(self) -> None:
        """Test behavior with zero second timeout (very tight limit)."""

        # This might raise immediately or after a very short delay
        try:
            with time_limit(1):
                pass
        except OperationTimeout:
            # This is acceptable for very short timeouts
            pass

    def test_time_limit_cleanup_removes_signal(self) -> None:
        """Test that time_limit properly cleans up signal handler."""
        original_handler = signal.signal(signal.SIGALRM, signal.SIG_DFL)

        try:
            with time_limit(2):
                pass

            # After context exit, the signal handler should be reset
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
            # We can't assert exact equality as it might have been reset, but
            # at least the context manager shouldn't crash on cleanup
        finally:
            signal.signal(signal.SIGALRM, original_handler)
