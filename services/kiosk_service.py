"""
services/kiosk_service.py
-------------------------
Implements the Kiosk State Manager and Transaction Manager for Front Desk Reception.

Architecture:
- KioskStateManager: Translates vision DetectionResult observations into
  the two-step verification workflow:
    Step 1: Face Identification (Pehle Face Detect)
    Step 2: Weapon Verification (Than Weapon Detect)
  Session end is handled MANUALLY from the Active Shooters desk panel.
- TransactionManager: Coordinates explicit database transactions (Attendance,
  Sessions, Weapon Events).
"""

from __future__ import annotations

import time
from datetime import datetime, date
from typing import Optional, Dict, Any

from models.detection_result import DetectionResult
from models.kiosk_state import KioskState, TransactionType, KioskContext
from services import attendance_service, session_service, event_service
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
        force_mode: str = "Auto (Smart Detect)",
    ) -> KioskContext:
        """
        Evaluate new detection result and update the two-step verification state.
        Enforces sequential flow:
          Step 1 -> Face Confirmed (user identity locked-in)
          Step 2 -> Weapon Verified (only runs after Step 1)
        Does NOT perform any automatic session end via camera.
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
            if det.weapon_detected and det.weapon_confidence >= 0.45:
                self.weapon_stability_count += 1
                self.context.weapon_type = det.weapon_type or "Firearm"
                self.context.weapon_category = det.weapon_category or "Firearm"
                self.context.weapon_confidence = det.weapon_confidence
                self.context.weapon_details = det.weapon_details

                if self.weapon_stability_count >= 1:
                    self.context.current_state = KioskState.READY_FOR_CHECKIN
            else:
                if self.context.weapon_type is None:
                    self.context.current_state = KioskState.USER_IDENTIFIED

        self.context.state_timestamp = time.time()
        return self.context


class TransactionManager:
    """Handles explicit business transactions against PostgreSQL."""

    @staticmethod
    def start_session(
        ctx: KioskContext,
        camera_id: str,
        lane_id: str,
        cooldown_cache: dict,
        cooldown_seconds: int = 5,
    ) -> Dict[str, Any]:
        """
        Execute Check-In: Creates Attendance entry, starts Session, and logs Weapon Event.
        """
        if not ctx.user_id:
            raise ValueError("Cannot start session: No user identified.")

        uid = ctx.user_id
        weapon_name = ctx.weapon_type or "Firearm"
        weapon_conf = ctx.weapon_confidence or 0.85

        # 1. Create or fetch Attendance Record
        att_id = attendance_service.create_attendance(uid)

        # 2. Start Range Session
        sess_id = session_service.start_session(uid, lane_id)

        # 3. Log Inward Weapon Event
        evt_id = event_service.log_weapon_event(
            user_id=uid,
            session_id=sess_id,
            weapon_type=weapon_name,
            confidence=weapon_conf,
            camera_id=camera_id,
            lane_id=lane_id,
            cooldown_cache=cooldown_cache,
            cooldown_seconds=cooldown_seconds,
        )

        now_str = datetime.now().strftime("%I:%M:%S %p")
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
        Manually check-out a shooter and end their range session from the desk panel.
        """
        from services import session_service, attendance_service
        # Close session
        session_service.end_session(session_id)
        # Close attendance
        out_info = attendance_service.check_out_user(user_id)
        return out_info
