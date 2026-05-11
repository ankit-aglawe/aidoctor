"""Drop stale user rows from a pandas DataFrame based on `last_seen` age."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd


def drop_stale_users(
    users: pd.DataFrame,
    max_age_days: int = 90,
    now: datetime | None = None,
    column: str = "last_seen",
) -> pd.DataFrame:
    """Return a new DataFrame with rows whose `last_seen` is within `max_age_days`.

    The input frame is not mutated. Rows where `last_seen` is NaT are treated
    as stale and dropped, matching the intent of "remove records I can't
    confirm are fresh."

    Args:
        users: Source frame. Must contain `column`.
        max_age_days: Inclusive freshness window in days.
        now: Reference timestamp; defaults to current UTC time. Pass an
            explicit value in tests to keep them deterministic.
        column: Name of the timestamp column to compare against.

    Returns:
        A new DataFrame containing only fresh rows, with the original index
        preserved.

    Raises:
        KeyError: If `column` is not present in `users`.
        ValueError: If `max_age_days` is negative.
    """
    if column not in users.columns:
        raise KeyError(f"DataFrame is missing required column: {column!r}")
    if max_age_days < 0:
        raise ValueError(f"max_age_days must be non-negative, got {max_age_days}")

    reference = now if now is not None else datetime.now(timezone.utc)
    cutoff = pd.Timestamp(reference) - timedelta(days=max_age_days)

    last_seen = pd.to_datetime(users[column], errors="coerce", utc=True)
    cutoff_tz = cutoff if cutoff.tzinfo is not None else cutoff.tz_localize("UTC")

    fresh_mask = last_seen.notna() & (last_seen >= cutoff_tz)
    return users.loc[fresh_mask].copy()
