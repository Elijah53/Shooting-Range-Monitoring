"""
services/event_service.py
--------------------------
Weapon event logging and detection/validation orchestration.
All database writes execute within atomic transactions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import streamlit as st
from database.database import execute, fetch_all, fetch_one, fetch_scalar, transaction
from models.event import WeaponEvent


# ── Logging ───────────────────────────────────────────────────────────────────

def log_weapon_event(
    user_id: int,
    session_id: int,
    weapon_type: str,
    confidence: float,
    camera_id: Optional[str],
    lane_id: Optional[str],
    cooldown_cache: dict,           # {(user_id, weapon_type): datetime}
    cooldown_seconds: int,
) -> Optional[int]:
    """
    Insert a weapon_event row only if outside the cooldown window.
    """
    cache_key = (user_id, weapon_type)
    last_logged = cooldown_cache.get(cache_key)
    now_dt = datetime.now()

    if last_logged is not None:
        elapsed = (now_dt - last_logged).total_seconds()
        if elapsed < cooldown_seconds:
            return None  # within cooldown window — suppress duplicate

    row = fetch_one(
        """
        INSERT INTO weapon_events
            (session_id, user_id, weapon_type, confidence, camera_id, lane_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING event_id
        """,
        (session_id, user_id, weapon_type, round(confidence, 4), camera_id, lane_id),
    )
    if row:
        cooldown_cache[cache_key] = now_dt
        return row["event_id"]
    return None


def set_manual_weapon_type(event_id: int, weapon_type: str, verified_by: str) -> None:
    """Record a manual human override/verification for a weapon event."""
    execute(
        "UPDATE weapon_events SET manual_weapon_type = %s, "
        "manually_verified_by = %s, manually_verified_at = NOW() "
        "WHERE event_id = %s",
        (weapon_type, verified_by, event_id),
    )


# ── Detection / validation workflow ──────────────────────────────────────────

@dataclass
class FrameResult:
    """Summary returned after processing one frame."""
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    face_confidence: float = 0.0
    face_recognized: bool = False

    weapon_detected: bool = False
    weapon_type: Optional[str] = None
    weapon_confidence: float = 0.0
    weapon_bbox: Optional[tuple] = None

    attendance_id: Optional[int] = None
    session_id: Optional[int] = None
    event_id: Optional[int] = None

    status_message: str = "No user / weapon detected"


def process_frame(
    face_result: tuple,          # (user_id|None, name|None, confidence)
    weapon_detections: list,     # list of Detection named-tuples
    lane_id: str,
    camera_id: Optional[str],
    cooldown_cache: dict,
    cooldown_seconds: int,
    confidence_threshold: float,
) -> FrameResult:
    """
    Apply validation rules to one frame's detection results and create DB rows
    inside an atomic transaction.
    """
    uid, uname, face_conf = face_result
    face_recognized = uid is not None

    best_detection = None
    for det in weapon_detections:
        if det.confidence >= confidence_threshold:
            if best_detection is None or det.confidence > best_detection.confidence:
                best_detection = det
    weapon_detected = best_detection is not None

    res = FrameResult(
        user_id=uid,
        user_name=uname,
        face_confidence=face_conf,
        face_recognized=face_recognized,
        weapon_detected=weapon_detected,
    )

    if best_detection:
        res.weapon_type = best_detection.weapon_type
        res.weapon_confidence = best_detection.confidence
        res.weapon_bbox = best_detection.bbox

    if face_recognized and weapon_detected:
        today = date.today()
        now_dt = datetime.now()
        cache_key = (uid, best_detection.weapon_type)

        with transaction() as conn:
            # 1. Attendance
            att_row = fetch_one(
                "SELECT attendance_id FROM attendance WHERE user_id = %s AND status = 'Active' AND entry_time::date = %s LIMIT 1",
                (uid, today),
                conn=conn,
            )
            if att_row:
                att_id = att_row["attendance_id"]
            else:
                new_att = fetch_one(
                    "INSERT INTO attendance (user_id, status) VALUES (%s, 'Active') RETURNING attendance_id",
                    (uid,),
                    conn=conn,
                )
                att_id = new_att["attendance_id"] if new_att else None

            # 2. Session
            sess_row = fetch_one(
                "SELECT session_id FROM sessions WHERE user_id = %s AND status = 'Active' LIMIT 1",
                (uid,),
                conn=conn,
            )
            if sess_row:
                sess_id = sess_row["session_id"]
            else:
                new_sess = fetch_one(
                    "INSERT INTO sessions (user_id, lane_id, status) VALUES (%s, %s, 'Active') RETURNING session_id",
                    (uid, lane_id),
                    conn=conn,
                )
                sess_id = new_sess["session_id"] if new_sess else None

            # 3. Weapon event
            last_logged = cooldown_cache.get(cache_key)
            cooldown_ok = True
            if last_logged is not None:
                elapsed = (now_dt - last_logged).total_seconds()
                if elapsed < cooldown_seconds:
                    cooldown_ok = False

            evt_id = None
            if cooldown_ok:
                new_evt = fetch_one(
                    """
                    INSERT INTO weapon_events
                        (session_id, user_id, weapon_type, confidence, camera_id, lane_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING event_id
                    """,
                    (sess_id, uid, best_detection.weapon_type, round(best_detection.confidence, 4), camera_id, lane_id),
                    conn=conn,
                )
                evt_id = new_evt["event_id"] if new_evt else None

        if cooldown_ok and evt_id is not None:
            cooldown_cache[cache_key] = now_dt

        res.attendance_id = att_id
        res.session_id = sess_id
        res.event_id = evt_id
        res.status_message = (
            f"Face recognized: {uname} | Weapon detected: {best_detection.weapon_type} "
            f"({best_detection.confidence:.0%} confidence)"
        )

    elif face_recognized and not weapon_detected:
        res.status_message = f"Face recognized: {uname} | Weapon: Not detected"

    elif not face_recognized and weapon_detected:
        res.status_message = (
            f"Weapon detected: {best_detection.weapon_type} "
            f"({best_detection.confidence:.0%} confidence) — User not identified"
        )

    else:
        res.status_message = "No user / weapon detected"

    return res


# ── Query helpers ─────────────────────────────────────────────────────────────

def get_events(
    user_id: Optional[int] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    weapon_type: Optional[str] = None,
    camera_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    from_date = from_date or date_from
    to_date = to_date or date_to
    clauses: list[str] = []
    params: list = []

    if user_id is not None:
        clauses.append("e.user_id = %s")
        params.append(user_id)
    if from_date is not None:
        clauses.append("e.detected_at::date >= %s")
        params.append(from_date)
    if to_date is not None:
        clauses.append("e.detected_at::date <= %s")
        params.append(to_date)
    if weapon_type:
        clauses.append("e.weapon_type = %s")
        params.append(weapon_type)
    if camera_id:
        clauses.append("e.camera_id = %s")
        params.append(camera_id)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT e.*, u.name AS user_name, u.name AS name
        FROM weapon_events e
        LEFT JOIN users u ON u.user_id = e.user_id
        {where}
        ORDER BY e.detected_at DESC
    """
    return fetch_all(sql, tuple(params) if params else None)


@st.cache_data(ttl=30)
def count_events_today() -> int:
    """Count weapon events for today. Cached 30 s."""
    today = date.today()
    return (
        fetch_scalar(
            "SELECT COUNT(*) FROM weapon_events WHERE detected_at::date = %s",
            (today,),
        )
        or 0
    )


def get_distinct_weapon_types() -> list[str]:
    rows = fetch_all("SELECT DISTINCT weapon_type FROM weapon_events ORDER BY weapon_type")
    return [r["weapon_type"] for r in rows]
