"""
Fuvay — Cursor-based Pagination
Never offset — cursor is always a base64-encoded last-item ID + timestamp.
Clients get next_cursor and prev_cursor, never page numbers.
"""
import base64
import json
from dataclasses import dataclass
from datetime import datetime


DEFAULT_LIMIT = 25
MAX_LIMIT = 100


@dataclass
class CursorPage:
    items: list
    total: int | None
    limit: int
    has_next: bool
    has_prev: bool
    next_cursor: str | None = None
    prev_cursor: str | None = None

    def to_meta(self) -> dict:
        return {
            "total": self.total,
            "limit": self.limit,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
            "next_cursor": self.next_cursor,
            "prev_cursor": self.prev_cursor,
        }


def encode_cursor(item_id: str, created_at: datetime) -> str:
    data = {"id": item_id, "ts": created_at.isoformat()}
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def decode_cursor(cursor: str) -> dict | None:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return data
    except Exception:
        return None


def parse_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    return min(max(1, limit), MAX_LIMIT)


def paginate(items: list, limit: int, has_prev: bool = False, total: int | None = None) -> CursorPage:
    """
    Given items fetched (limit + 1 to detect next page),
    return a CursorPage with correct has_next and next_cursor.
    """
    has_next = len(items) > limit
    if has_next:
        items = items[:limit]

    next_cursor = None
    if has_next and items:
        last = items[-1]
        last_id = str(getattr(last, "id", ""))
        last_ts = getattr(last, "created_at", datetime.utcnow())
        next_cursor = encode_cursor(last_id, last_ts)

    return CursorPage(
        items=items,
        total=total,
        limit=limit,
        has_next=has_next,
        has_prev=has_prev,
        next_cursor=next_cursor,
    )
