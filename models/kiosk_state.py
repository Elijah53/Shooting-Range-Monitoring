"""
models/kiosk_state.py
---------------------
State definitions and context models for the Front Desk Kiosk State Machine.
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


class KioskState(str, Enum):
    """Lifecycle states of the front desk counter kiosk."""
    IDLE = "IDLE"
    FACE_DETECTED = "FACE_DETECTED"
    USER_IDENTIFIED = "USER_IDENTIFIED"
    WEAPON_DETECTED = "WEAPON_DETECTED"
    READY_FOR_CHECKIN = "READY_FOR_CHECKIN"
    SESSION_ACTIVE = "SESSION_ACTIVE"
    READY_FOR_CHECKOUT = "READY_FOR_CHECKOUT"
    SESSION_COMPLETED = "SESSION_COMPLETED"
    
    # Failure / Alert States
    MULTIPLE_FACES_DETECTED = "MULTIPLE_FACES_DETECTED"
    FACE_NOT_RECOGNIZED = "FACE_NOT_RECOGNIZED"
    WEAPON_NOT_DETECTED = "WEAPON_NOT_DETECTED"
    CAMERA_OFFLINE = "CAMERA_OFFLINE"


class TransactionType(str, Enum):
    """Type of transaction being processed at the counter."""
    CHECK_IN = "CHECK_IN"
    CHECK_OUT = "CHECK_OUT"
    NONE = "NONE"


@dataclass
class KioskContext:
    """Holds active session, user, and transaction state at the desk."""
    current_state: KioskState = KioskState.IDLE
    transaction_type: TransactionType = TransactionType.NONE

    # Identified Shooter Details
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    face_confidence: float = 0.0
    face_confirmed: bool = False  # True once face stage is locked-in

    # Verified Weapon Details
    weapon_type: Optional[str] = None
    weapon_category: Optional[str] = None
    weapon_confidence: float = 0.0
    weapon_details: Optional[str] = None

    # Active Database Records (if user is currently inside)
    active_attendance_id: Optional[int] = None
    active_session_id: Optional[int] = None
    entry_time: Optional[str] = None
    duration_str: Optional[str] = None

    # Completed Transaction Snapshot
    last_completed_summary: Optional[Dict[str, Any]] = None
    state_timestamp: float = 0.0

    def reset(self) -> None:
        """Reset context to fresh idle state."""
        self.current_state = KioskState.IDLE
        self.transaction_type = TransactionType.NONE
        self.user_id = None
        self.user_name = None
        self.face_confidence = 0.0
        self.face_confirmed = False
        self.weapon_type = None
        self.weapon_category = None
        self.weapon_confidence = 0.0
        self.weapon_details = None
        self.active_attendance_id = None
        self.active_session_id = None
        self.entry_time = None
        self.duration_str = None
        self.last_completed_summary = None
