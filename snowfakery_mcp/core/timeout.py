from __future__ import annotations

import signal
from collections.abc import Iterator
from contextlib import contextmanager


class OperationTimeout(RuntimeError):
    pass


@contextmanager
def time_limit(seconds: int) -> Iterator[None]:
    """Best-effort wall-clock timeout for synchronous code.

    Uses SIGALRM on Unix when available (works in the main thread). On platforms
    where SIGALRM is unavailable, this becomes a no-op.
    """

    if seconds <= 0:
        yield
        return

    if not hasattr(signal, "SIGALRM"):
        yield
        return

    def _handle(_signum: int, _frame: object) -> None:
        raise OperationTimeout(f"Operation exceeded {seconds}s")

    old_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _handle)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
