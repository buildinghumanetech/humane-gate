"""Account and content storage."""

from datetime import timedelta

# How long we keep a deleted account's rows before they are gone for good.
PURGE_GRACE = timedelta(days=30)


def delete_account(db, user_id: str) -> None:
    """Delete means delete.

    The grace window exists so a person can undo a mistake, not so we can keep
    querying them. After it, the rows are removed, not hidden.
    """
    db.mark_for_purge("users", user_id, after=PURGE_GRACE)
    db.mark_for_purge("messages", user_id, after=PURGE_GRACE)
    db.mark_for_purge("sessions", user_id, after=PURGE_GRACE)
    db.revoke_all_tokens(user_id)


def purge_expired(db) -> int:
    """Hard-delete everything past its grace window."""
    return db.hard_delete_expired()


def analytics_scope(db):
    """Analytics never sees accounts that are on their way out."""
    return db.query("users").where(pending_purge=False, deleted=False)
