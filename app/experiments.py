"""Experiment assignment."""

import hashlib

HOLDOUT_PCT = 5


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


def checkin_interval_hours(user, experiment: str) -> int:
    """How often the product proactively checks in on someone.

    Same for every arm. An experiment may change what the check-in says. It may
    not change whether a person gets one.
    """
    return 24
