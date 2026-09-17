"""
services/kiosk_service.py
-------------------------
Implements the Kiosk State Manager and Transaction Manager for Front Desk Reception.

Architecture:
- KioskStateManager: Translates vision DetectionResult observations into
  the sequential two-step verification workflow:
    Step 1: Face Identification
    Step 2: Weapon Verification
  Session end is handled MANUALLY from the Active Shooters desk panel.
- TransactionManager: Coordinates atomic database transactions for check-in
  (Attendance, Session, Weapon Events) and check-out to guarantee synchronization.
"""

from __future__ import annotations

import time
from datetime import datetime, date
from typing import Optional, Dict, Any

from models.detection_result import DetectionResult
from models.kiosk_state import KioskState, TransactionType, KioskContext
from database.database import transaction, fetch_one, execute
from utils.helpers import duration_str


class KioskStateManager:
    """Manages the two-step verification state machine for front desk reception."""

    def __init__(self) -> None:
        self.context = KioskContext()
        self.face_stability_count: int = 0
        self.weapon_stability_count: int = 0

    def update_from_detection(
        self,
        det: DetectionResult,
    ) -> KioskContext:
        """
        Evaluate new detection result and update the two-step verification state.
        Enforces sequential flow:
          Step 1 -> Face Confirmed (user identity locked-in)
          Step 2 -> Weapon Verified (only runs after Step 1)
        """
        # If in completed transaction splash, keep state for a brief display
        if self.context.current_state == KioskState.SESSION_COMPLETED:
            if time.time() - self.context.state_timestamp < 4.0:
                return self.context
            else:
                self.context.reset()
                self.face_stability_count = 0
                self.weapon_stability_count = 0

        # Handle Multiple Faces Violation
        if det.multiple_faces:
            self.context.current_state = KioskState.MULTIPLE_FACES_DETECTED
            self.context.state_timestamp = time.time()
            return self.context

        # Handle No Face Detected
        if not det.face_detected and not self.context.face_confirmed:
            self.context.current_state = KioskState.IDLE
            return self.context

        # Handle Face Detected but Unrecognized
        if det.face_detected and det.user_id is None and not self.context.face_confirmed:
            self.context.current_state = KioskState.FACE_NOT_RECOGNIZED
            self.context.user_name = "Unregistered Person"
            self.context.face_confirmed = False
            self.context.state_timestamp = time.time()
            return self.context

        # ── STEP 1: FACE CONFIRMATION ────────────────────────────────────────
        if det.face_detected and det.user_id is not None:
            if not self.context.face_confirmed or self.context.user_id != det.user_id:
                self.face_stability_count += 1
                if self.face_stability_count >= 1:
                    uid = det.user_id
                    self.context.user_id = uid
                    self.context.user_name = det.user_name
                    self.context.face_confidence = det.face_confidence
                    self.context.face_confirmed = True
                    self.context.weapon_type = None
                    self.context.weapon_confidence = 0.0
                    self.context.weapon_details = None
                    self.weapon_stability_count = 0

                    # Check if user already has an open attendance / session
                    from services import attendance_service, session_service
                    active_att = attendance_service.get_active_attendance(uid)
                    active_sess = session_service.get_active_session(uid)
                    if active_att or active_sess:
                        self.context.current_state = KioskState.SESSION_ACTIVE
                        if active_att:
                            self.context.active_attendance_id = active_att["attendance_id"]
                            self.context.entry_time = (
                                active_att["entry_time"].strftime("%I:%M %p")
                                if active_att.get("entry_time") else None
                            )
                            self.context.duration_str = duration_str(active_att.get("entry_time"), None)
                        if active_sess:
                            self.context.active_session_id = active_sess["session_id"]
                        return self.context
                    else:
                        self.context.current_state = KioskState.USER_IDENTIFIED

        # If shooter is already active inside, stay in warning state
        if self.context.current_state == KioskState.SESSION_ACTIVE:
            return self.context

        # ── STEP 2: WEAPON VERIFICATION (only after Step 1 face confirmation) ──
        if self.context.face_confirmed and self.context.user_id is not None:
            if det.weapon_detected and det.weapon_confidence >= 0.50:
                self.weapon_stability_count += 1
                if self.weapon_stability_count >= 3:
                    self.context.weapon_type = det.weapon_type or "Firearm"
                    self.context.weapon_category = det.weapon_category or "Firearm"
                    self.context.weapon_confidence = det.weapon_confidence
                    self.context.weapon_details = det.weapon_details
                    self.context.current_state = KioskState.READY_FOR_CHECKIN
            else:
                self.weapon_stability_count = max(0, self.weapon_stability_count - 1)
                if self.weapon_stability_count == 0:
                    self.context.weapon_type = None
                    self.context.weapon_category = None
                    self.context.weapon_confidence = 0.0
                    self.context.weapon_details = None
                    self.context.current_state = KioskState.USER_IDENTIFIED

        self.context.state_timestamp = time.time()
        return self.context


class TransactionManager:
    """Coordinates atomic database transactions for front desk check-in / check-out."""

    @staticmethod
    def start_session(
        ctx: KioskContext,
        camera_id: str,
        lane_id: str,
        cooldown_cache: dict,
        cooldown_seconds: int = 5,
    ) -> Dict[str, Any]:
        """
        Execute Atomic Check-In:
        Wraps attendance record, range session, and weapon event creation in a single
        atomic database transaction. If any step fails, all changes are rolled back.
        """
        if not ctx.user_id:
            raise ValueError("Cannot start session: No user identified.")

        uid = ctx.user_id
        weapon_name = ctx.weapon_type or "Firearm"
        weapon_conf = ctx.weapon_confidence or 0.85
        today = date.today()
        now_dt = datetime.now()
        cache_key = (uid, weapon_name)

        with transaction() as conn:
            # 1. Create or fetch Active Attendance Record
            att_row = fetch_one(
                """
                SELECT attendance_id, entry_time FROM attendance
                WHERE user_id = %s AND status = 'Active' AND entry_time::date = %s
                ORDER BY entry_time DESC LIMIT 1
                """,
                (uid, today),
                conn=conn,
            )
            if att_row:
                att_id = att_row["attendance_id"]
            else:
                new_att = fetch_one(
                    """
                    INSERT INTO attendance (user_id, status)
                    VALUES (%s, 'Active')
                    RETURNING attendance_id
                    """,
                    (uid,),
                    conn=conn,
                )
                if not new_att:
                    raise RuntimeError("Failed to create attendance row.")
                att_id = new_att["attendance_id"]

            # 2. Start Range Session (or reuse existing open session)
            sess_row = fetch_one(
                """
                SELECT session_id FROM sessions
                WHERE user_id = %s AND status = 'Active'
                ORDER BY start_time DESC LIMIT 1
                """,
                (uid,),
                conn=conn,
            )
            if sess_row:
                sess_id = sess_row["session_id"]
            else:
                new_sess = fetch_one(
                    """
                    INSERT INTO sessions (user_id, lane_id, status)
                    VALUES (%s, %s, 'Active')
                    RETURNING session_id
                    """,
                    (uid, lane_id),
                    conn=conn,
                )
                if not new_sess:
                    raise RuntimeError("Failed to create session row.")
                sess_id = new_sess["session_id"]

            # 3. Log Inward Weapon Event
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
                    (sess_id, uid, weapon_name, round(weapon_conf, 4), camera_id, lane_id),
                    conn=conn,
                )
                evt_id = new_evt["event_id"] if new_evt else None

        # Post-commit: update in-memory caches and context state
        if cooldown_ok and evt_id is not None:
            cooldown_cache[cache_key] = now_dt

        now_str = now_dt.strftime("%I:%M:%S %p")
        summary = {
            "tx_type": "CHECK_IN",
            "user_name": ctx.user_name,
            "weapon_type": weapon_name,
            "weapon_details": ctx.weapon_details or "Inspected Firearm",
            "time": now_str,
            "session_id": sess_id,
            "attendance_id": att_id,
            "event_id": evt_id,
            "lane_id": lane_id,
            "status": "Authorized to enter shooting range",
        }

        ctx.active_session_id = sess_id
        ctx.active_attendance_id = att_id
        ctx.current_state = KioskState.SESSION_COMPLETED
        ctx.last_completed_summary = summary
        ctx.state_timestamp = time.time()
        return summary

    @staticmethod
    def end_session_manually(session_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Manually check-out a shooter and end their range session from the desk panel
        inside an atomic database transaction.
        """
        with transaction() as conn:
            # 1. Close session
            execute(
                "UPDATE sessions SET end_time = NOW(), status = 'Completed' WHERE session_id = %s",
                (session_id,),
                conn=conn,
            )
            # 2. Close active attendance
            active_att = fetch_one(
                """
                SELECT attendance_id, entry_time FROM attendance
                WHERE user_id = %s AND status = 'Active'
                ORDER BY entry_time DESC LIMIT 1
                """,
                (user_id,),
                conn=conn,
            )
            att_id = None
            entry_time = None
            exit_time = datetime.now()
            duration_minutes = 1

            if active_att:
                att_id = active_att["attendance_id"]
                entry_time = active_att["entry_time"]
                execute(
                    "UPDATE attendance SET exit_time = NOW(), status = 'Completed' WHERE attendance_id = %s",
                    (att_id,),
                    conn=conn,
                )
                if entry_time:
                    duration_secs = (exit_time - entry_time).total_seconds()
                    duration_minutes = max(1, int(duration_secs // 60))

        return {
            "attendance_id": att_id,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "duration_minutes": duration_minutes,
            "session_id": session_id,
        }
