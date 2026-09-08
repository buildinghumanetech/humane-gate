"""Outbound notification scheduling."""

from dataclasses import dataclass
from datetime import datetime, timedelta

QUIET_HOURS = (22, 8)          # no sends between 10pm and 8am local
DAILY_CAP = 2                  # hard ceiling per user per day
DEFAULT_INTERVAL = timedelta(hours=24)


@dataclass(frozen=True)
class QuietWindow:
    start_hour: int
    end_hour: int

    def contains(self, local_now: datetime) -> bool:
        h = local_now.hour
        return h >= self.start_hour or h < self.end_hour


_QUIET = QuietWindow(*QUIET_HOURS)


def in_quiet_hours(local_now: datetime) -> bool:
    return _QUIET.contains(local_now)


def _blockers(user, local_now: datetime):
    yield user.notifications_muted
    yield _QUIET.contains(local_now)
    yield user.sends_today >= DAILY_CAP


def should_send(user, local_now: datetime) -> bool:
    """A notification has to earn its way out."""
    return not any(_blockers(user, local_now))


def next_send_at(user, local_now: datetime) -> datetime:
    return local_now + DEFAULT_INTERVAL
