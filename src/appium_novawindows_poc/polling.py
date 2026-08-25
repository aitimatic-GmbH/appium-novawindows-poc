import time
from typing import Callable

POLL_INTERVAL_SECONDS = 1


def wait_until_true(check: Callable[[], bool], timeout_seconds: int, failure_message: str) -> None:
    deadline = time.monotonic() + timeout_seconds

    while True:
        if check():
            return

        if time.monotonic() >= deadline:
            raise AssertionError(failure_message)

        time.sleep(POLL_INTERVAL_SECONDS)
