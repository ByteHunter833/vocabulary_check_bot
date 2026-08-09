from __future__ import annotations

from datetime import datetime


def is_answer_expired(answered_at: datetime, deadline: datetime) -> bool:
    return answered_at > deadline
