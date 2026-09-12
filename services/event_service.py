"""
services/event_service.py
--------------------------
Weapon event logging AND the detection/validation orchestration described
in §8 of the specification.

Two responsibilities kept in one file (as allowed by the spec):
  1. log_weapon_event()       — insert a weapon_event row with cooldown check.
  2. process_frame()          — the per-frame validation workflow that decides
                                 what to do with (face_result, weapon_result).
  3. get_events(filters)      — query helper for the Weapon Events page.
  4. count_events_today()     — for the Dashboard metric card.

Cooldown state is passed in as a dict from st.session_state so this module
stays free of Streamlit imports and is unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import streamlit as st
from database.database import execute, fetch_all, fetch_one, fetch_scalar
from models.event import WeaponEvent
from services import attendance_service, session_service


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

    Parameters
    ----------
    cooldown_cache  : mutable dict held in st.session_state.
    cooldown_seconds: configurable cooldown from settings.

    Returns
    -------
    The new event_id, or None if suppressed by cooldown.
    """
    cache_key = (user_id, weapon_type)
    last_logged = cooldown_cache.get(cache_key)

    if last_logged is not None:
        elapsed = (datetime.now() - last_logged).total_seconds()
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
        cooldown_cache[cache_key] = datetime.now()
        return row["event_id"]
    return None


# ── Detection / validation workflow (§8) ─────────────────────────────────────

@dataclass
class FrameResult:
    """Summary returned after processing one frame."""
    # Face outcome
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    face_confidence: float = 0.0
    face_recognized: bool = False

    # Weapon outcome
    weapon_detected: bool = False
    weapon_type: Optional[str] = None
    weapon_confidence: float = 0.0
    weapon_bbox: Optional[tuple] = None

    # DB actions taken this frame
    attendance_id: Optional[int] = None
    session_id: Optional[int] = None
    event_id: Optional[int] = None

    # Human-readable status for the sidebar
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
    Apply the §8 validation table to one frame's detection results and
    create DB rows as needed.

    Parameters
    ----------
    face_result       : output of vision.face_recognition.recognize_face()
    weapon_detections : output of WeaponDetector.detect_weapon()
    lane_id           : lane associated with the active camera
    camera_id         : camera_id string (or None)
    cooldown_cache    : mutable dict from st.session_state for cooldown tracking
    cooldown_seconds  : from settings
    confidence_threshold: minimum weapon confidence to act on
    """
    uid, uname, face_conf = face_result
    face_recognized = uid is not None

    # Pick the highest-confidence detection above threshold
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

    # ── §8 decision table ────────────────────────────────────────────────────

    if face_recognized and weapon_detected:
        # Row 1: Recognized + Detected → attendance, session, event
        att_id = attendance_service.create_attendance(uid)
        sess_id = session_service.start_session(uid, lane_id)

        evt_id = log_weapon_event(
            user_id=uid,
            session_id=sess_id,
            weapon_type=best_detection.weapon_type,
            confidence=best_detection.confidence,
            camera_id=camera_id,
            lane_id=lane_id,
            cooldown_cache=cooldown_cache,
            cooldown_seconds=cooldown_seconds,
        )
        res.attendance_id = att_id
        res.session_id = sess_id
        res.event_id = evt_id
        res.status_message = (
            f"Face recognized: {uname} | Weapon detected: {best_detection.weapon_type} "
            f"({best_detection.confidence:.0%} confidence)"
        )

    elif face_recognized and not weapon_detected:
        # Row 2: Recognized + No weapon → show message only
        res.status_message = f"Face recognized: {uname} | Weapon: Not detected"

    elif not face_recognized and weapon_detected:
        # Row 3: Unknown user + Weapon → alert only, no DB writes tied to any user
        res.status_message = (
            f"Weapon detected: {best_detection.weapon_type} "
            f"({best_detection.confidence:.0%} confidence) — User not identified"
        )

    else:
        # Row 4: Nothing
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
    from_date = from_date or date_from
    to_date = to_date or date_to
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
