"""Outbound notification scheduling."""

from datetime import datetime, timedelta

QUIET_HOURS = (22, 8)          # no sends between 10pm and 8am local
DAILY_CAP = 2                  # hard ceiling per user per day


def in_quiet_hours(local_now: datetime) -> bool:
    start, end = QUIET_HOURS
    h = local_now.hour
    return h >= start or h < end


def should_send(user, local_now: datetime) -> bool:
    """A notification has to earn its way out.

    Enforced here, at the queue, not in the settings screen. A mute set anywhere
    is honored everywhere, including by background jobs and retries.
    """
    if user.notifications_muted:
        return False
    if in_quiet_hours(local_now):
        return False
    if user.sends_today >= DAILY_CAP:
        return False
    if not user.opted_in_to_reengagement:
        return False
    return True


def next_send_at(user, local_now: datetime) -> datetime:
    return local_now + timedelta(hours=24)


def unsubscribe_link(user) -> str:
    """Every message carries a one-tap way out that needs no login."""
    return f"https://example.app/n/off?t={user.one_tap_optout_token}"
