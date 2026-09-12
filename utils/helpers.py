"""
utils/helpers.py
----------------
Shared utility functions used across pages and services.
"""

from datetime import datetime
from typing import Optional


# ── Badge / label helpers ─────────────────────────────────────────────────────

STATUS_COLORS = {
    "Active": "🟢",
    "Online": "🟢",
    "Completed": "⚪",
    "Offline": "🔴",
    "Inactive": "🔴",
    "Available": "🟢",
    "In Use": "🟡",
    "Maintenance": "🔴",
}


def status_badge(status: str) -> str:
    """Return a status string decorated with a coloured emoji dot."""
    icon = STATUS_COLORS.get(status, "⚫")
    return f"{icon} {status}"


# ── Date / time helpers ────────────────────────────────────────────────────────

def format_dt(dt: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format a datetime (or None) as a readable string."""
    if dt is None:
        return "—"
    return dt.strftime(fmt)


def fmt_time(dt: Optional[datetime], fmt: str = "%d %b %Y, %I:%M %p") -> str:
    """Format a datetime for display in tables. Alias used by all page files."""
    if dt is None:
        return "—"
    return dt.strftime(fmt)


def now_local() -> datetime:
    """Return current local datetime (timezone-naive for DB compatibility)."""
    return datetime.now()


def duration_str(start: Optional[datetime], end: Optional[datetime]) -> str:
    """Return a human-readable duration string."""
    if start is None:
        return "—"
    finish = end if end is not None else now_local()
    delta = finish - start
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "—"
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


# ── Confidence formatting ─────────────────────────────────────────────────────

def pct(value: float) -> str:
    """Format a 0-1 float as a percentage string."""
    return f"{value * 100:.1f}%"


# ── Weapon ID generation ──────────────────────────────────────────────────────

def next_weapon_id(existing_ids: list) -> str:
    """
    Generate the next sequential weapon ID (e.g. 'WPN-004') from a list
    of existing string IDs like ['WPN-001', 'WPN-002', 'WPN-003'].
    """
    nums = []
    for wid in existing_ids:
        try:
            nums.append(int(str(wid).split("-")[-1]))
        except (ValueError, IndexError):
            pass
    next_num = max(nums, default=0) + 1
    return f"WPN-{next_num:03d}"


# ── Misc ──────────────────────────────────────────────────────────────────────

def safe_int(value, default: int = 0) -> int:
    """Safely cast a value to int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
