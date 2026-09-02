import pytest

from appium_novawindows_poc import polling
from appium_novawindows_poc.polling import POLL_INTERVAL_SECONDS, wait_until_true


class FakeTime:
    """Ersatz für das time-Modul der Warteschleife, damit die Tests nicht echt warten."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class Check:
    """Zählende Prüfung; succeeds_on ist der Aufruf, ab dem sie wahr wird, None heißt nie."""

    def __init__(self, succeeds_on: int | None) -> None:
        self.succeeds_on = succeeds_on
        self.calls = 0

    def __call__(self) -> bool:
        self.calls += 1
        return self.succeeds_on is not None and self.calls >= self.succeeds_on


@pytest.fixture
def fake_time(monkeypatch):
    replacement = FakeTime()
    monkeypatch.setattr(polling, "time", replacement)
    return replacement


def test_wait_until_true_returns_without_waiting_when_the_check_holds(fake_time):
    check = Check(succeeds_on=1)

    wait_until_true(check, timeout_seconds=10, failure_message="unerreichbar")

    assert check.calls == 1
    assert fake_time.sleeps == []


def test_wait_until_true_returns_as_soon_as_the_check_holds(fake_time):
    check = Check(succeeds_on=3)

    wait_until_true(check, timeout_seconds=10, failure_message="unerreichbar")

    assert check.calls == 3


def test_wait_until_true_sleeps_the_configured_interval_between_attempts(fake_time):
    wait_until_true(Check(succeeds_on=3), timeout_seconds=10, failure_message="unerreichbar")

    assert fake_time.sleeps == [POLL_INTERVAL_SECONDS, POLL_INTERVAL_SECONDS]


def test_wait_until_true_raises_with_the_given_message(fake_time):
    with pytest.raises(AssertionError, match="Dialog blieb geschlossen"):
        wait_until_true(
            Check(succeeds_on=None),
            timeout_seconds=3,
            failure_message="Dialog blieb geschlossen",
        )


def test_wait_until_true_stops_at_the_timeout(fake_time):
    check = Check(succeeds_on=None)

    with pytest.raises(AssertionError):
        wait_until_true(check, timeout_seconds=3, failure_message="unerreichbar")

    assert fake_time.now == 3
    assert check.calls == 4


def test_wait_until_true_accepts_a_check_that_holds_at_the_deadline(fake_time):
    wait_until_true(Check(succeeds_on=4), timeout_seconds=3, failure_message="unerreichbar")

    assert fake_time.now == 3


def test_wait_until_true_checks_once_even_without_a_time_budget(fake_time):
    check = Check(succeeds_on=None)

    with pytest.raises(AssertionError):
        wait_until_true(check, timeout_seconds=0, failure_message="unerreichbar")

    assert check.calls == 1
    assert fake_time.sleeps == []
