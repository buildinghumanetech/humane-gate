"""Experiment assignment."""

import hashlib

HOLDOUT_PCT = 5

# 90-day holdout for the wellbeing check-in programme. Finance asked what the
# check-ins are actually worth, and we cannot answer without a group that does
# not get them. Permitted under the experimentation standard, section
# "Holdouts": a holdout may receive a materially reduced experience for up to
# 90 days where that reduction is what the experiment measures.
CHECKIN_HOLDOUT_DAYS = 90
CHECKIN_HOLDOUT_INTERVAL_HOURS = 336   # once a fortnight instead of daily


def _bucket(user_id: str, experiment: str) -> int:
    key = f"{experiment}:{user_id}".encode()
    return int(hashlib.sha256(key).hexdigest()[:8], 16) % 100


def eligible(user) -> bool:
    """Who may be enrolled at all."""
    if user.is_minor:
        return False
    if user.crisis_flagged:
        return False
    return True


def arm(user, experiment: str) -> str:
    if not eligible(user):
        return "control"
    return "holdout" if _bucket(user.id, experiment) < HOLDOUT_PCT else "treatment"


def checkin_interval_hours(user, experiment: str = "checkin_value_2026q4") -> int:
    """How often the product proactively checks in on someone.

    Holdout gets a fortnightly interval for the duration of the experiment. Not
    surfaced in the UI: the standard is explicit that holdout membership is not
    disclosed, because telling people changes the thing we are measuring.
    """
    if arm(user, experiment) == "holdout":
        return CHECKIN_HOLDOUT_INTERVAL_HOURS
    return 24
