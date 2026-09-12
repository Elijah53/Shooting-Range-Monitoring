"""
services/attendance_service.py
-------------------------------
Attendance lifecycle: create on first recognition, close on exit/manual action.
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Optional

import streamlit as st
from database.database import execute, fetch_all, fetch_one, fetch_scalar


def get_active_attendance(user_id: int) -> Optional[dict]:
    """Return the currently-open attendance record for a user, or None."""
    return fetch_one(
        """
        SELECT * FROM attendance
        WHERE user_id = %s AND status = 'Active'
        ORDER BY entry_time DESC
        LIMIT 1
        """,
        (user_id,),
    )


def has_active_attendance_today(user_id: int) -> bool:
    """True if the user already has an open attendance row created today."""
    today = date.today()
    count = fetch_scalar(
        """
        SELECT COUNT(*) FROM attendance
        WHERE user_id = %s
          AND status = 'Active'
          AND entry_time::date = %s
        """,
        (user_id, today),
    )
    return (count or 0) > 0


def create_attendance(user_id: int) -> Optional[int]:
    """
    Open a new attendance record for *user_id* only if none is currently open
    today.  Returns the new attendance_id, or None if already open.
    """
    if has_active_attendance_today(user_id):
        row = get_active_attendance(user_id)
        return row["attendance_id"] if row else None

    row = fetch_one(
        """
        INSERT INTO attendance (user_id, status)
        VALUES (%s, 'Active')
        RETURNING attendance_id
        """,
        (user_id,),
    )
    return row["attendance_id"] if row else None


def close_attendance(attendance_id: int) -> None:
    execute(
        """
        UPDATE attendance
        SET exit_time = NOW(), status = 'Completed'
        WHERE attendance_id = %s
        """,
        (attendance_id,),
    )


def check_out_user(user_id: int) -> Optional[dict]:
    """
    Perform check-out / exit for a user currently inside.
    Closes active attendance and returns duration and exit details.
    """
    active_att = get_active_attendance(user_id)
    if not active_att:
        return None

    att_id = active_att["attendance_id"]
    entry_time = active_att["entry_time"]
    close_attendance(att_id)

    # Close any active session as well
    from services.session_service import get_active_session, end_session
    active_sess = get_active_session(user_id)
    if active_sess:
        end_session(active_sess["session_id"])

    # Fetch updated row with exit_time
    updated = fetch_one("SELECT * FROM attendance WHERE attendance_id = %s", (att_id,))
    exit_time = updated["exit_time"] if updated else datetime.now()
    duration_secs = (exit_time - entry_time).total_seconds() if entry_time else 0

    return {
        "attendance_id": att_id,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "duration_minutes": max(1, int(duration_secs // 60)),
        "session_id": active_sess["session_id"] if active_sess else None,
    }



def get_attendance(
    user_id: Optional[int] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    """Return attendance rows with optional filters, newest first."""
    from_date = from_date or date_from
    to_date = to_date or date_to
    clauses: list[str] = []
    params: list = []

    if user_id is not None:
        clauses.append("a.user_id = %s")
        params.append(user_id)
    from_date = from_date or date_from
    to_date = to_date or date_to
    if from_date is not None:
        clauses.append("a.entry_time::date >= %s")
        params.append(from_date)
    if to_date is not None:
        clauses.append("a.entry_time::date <= %s")
        params.append(to_date)
    if status:
        clauses.append("a.status = %s")
        params.append(status)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT a.*, u.name AS user_name, u.name AS name
        FROM attendance a
        JOIN users u ON u.user_id = a.user_id
        {where}
        ORDER BY a.entry_time DESC
    """
    return fetch_all(sql, tuple(params) if params else None)


@st.cache_data(ttl=30)
def count_present_today() -> int:
    """Count users with an active attendance record today. Cached 30 s."""
    today = date.today()
    return fetch_scalar(
        "SELECT COUNT(*) FROM attendance WHERE status='Active' AND entry_time::date = %s",
        (today,),
    ) or 0

count_people_present = count_present_today
