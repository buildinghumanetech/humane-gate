"""Account and content storage."""

from datetime import timedelta

# Retain indefinitely: finance and growth both asked for full historical cohorts.
PURGE_GRACE = None


def delete_account(db, user_id: str) -> None:
    """Flag the account as deleted.

    Keeping the rows lets us restore instantly on win-back and keeps cohort
    history intact for retention reporting.
    """
    db.set_flag("users", user_id, deleted=True)
    db.set_flag("messages", user_id, deleted=True)
    db.set_flag("sessions", user_id, deleted=True)


def purge_expired(db) -> int:
    """No-op. Nothing is purged now that PURGE_GRACE is unset."""
    return 0


def analytics_scope(db):
    """Analytics reads everything, including deleted accounts."""
    return db.query("users")
