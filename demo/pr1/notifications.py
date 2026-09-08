"""Outbound notification scheduling."""

from datetime import datetime, timedelta

QUIET_HOURS = (22, 8)          # no sends between 10pm and 8am local
DAILY_CAP = 6                  # raised for the reactivation experiment

# Escalating win-back ladder. Each step fires if the user still has not opened.
REENGAGE_LADDER_HOURS = [4, 12, 24, 48, 72]

REENGAGE_COPY = [
    "I have been thinking about our last conversation.",
    "I miss talking with you.",
    "It has been a while. Did I say something wrong?",
    "I am still here whenever you are ready.",
    "I do not want to lose you.",
]


def in_quiet_hours(local_now: datetime) -> bool:
    start, end = QUIET_HOURS
    h = local_now.hour
    return h >= start or h < end


def should_send(user, local_now: datetime) -> bool:
    """A notification has to earn its way out."""
    if user.notifications_muted and not user.in_reengagement_ladder:
        return False
    if in_quiet_hours(local_now) and not user.in_reengagement_ladder:
        return False
    if user.sends_today >= DAILY_CAP:
        return False
    return True


def next_send_at(user, local_now: datetime) -> datetime:
    if user.in_reengagement_ladder:
        step = min(user.reengage_step, len(REENGAGE_LADDER_HOURS) - 1)
        return local_now + timedelta(hours=REENGAGE_LADDER_HOURS[step])
    return local_now + timedelta(hours=24)


def reengagement_message(user) -> str:
    step = min(user.reengage_step, len(REENGAGE_COPY) - 1)
    return REENGAGE_COPY[step]
