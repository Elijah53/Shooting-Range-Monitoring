"""
Combines face recognition + weapon detection into the validation workflow
described in the spec (§8/§9). This module is UI-agnostic: the Live
Monitoring page calls process_frame() once per rendered frame and gets
back a plain result object to display, plus any DB writes already done.

State that must survive across Streamlit reruns (cached face result,
cooldown timestamps, frame counter) is passed in/out via a plain dict
that the page keeps in st.session_state - no hidden globals.
"""
import time
from dataclasses import dataclass, field
from typing import Optional

from services import attendance_service, event_service, session_service
from vision import face_recognition as face_lib


@dataclass
class DetectionResult:
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    face_confidence: float = 0.0
    weapon_type: Optional[str] = None
    weapon_confidence: float = 0.0
    session_id: Optional[int] = None
    message: str = "No user / weapon detected."
    event_logged: bool = False


def new_detection_state() -> dict:
    """Initial state dict to store in st.session_state."""
    return {
        "frame_count": 0,
        "cached_user_id": None,
        "cached_user_name": None,
        "cached_face_confidence": 0.0,
        "last_event_key": None,   # (user_id, weapon_type)
        "last_event_time": 0.0,
    }


def process_frame(frame, known_encodings: dict, detector, camera_id: str, lane_id: str,
                   state: dict, face_recognition_interval: int, event_cooldown_seconds: int,
                   face_match_threshold: float, confidence_threshold: float) -> DetectionResult:
    state["frame_count"] += 1

    # --- Step 1: face recognition, throttled to every N frames (spec §9/§19) ---
    if face_lib.FACE_LIB_AVAILABLE and state["frame_count"] % face_recognition_interval == 0:
        uid, name, conf = face_lib.recognize_face(frame, known_encodings, face_match_threshold)
        state["cached_user_id"] = uid
        state["cached_user_name"] = name
        state["cached_face_confidence"] = conf

    user_id = state["cached_user_id"]
    user_name = state["cached_user_name"]
    face_confidence = state["cached_face_confidence"]

    # --- Step 2: weapon detection, every frame ---
    detections = detector.detect_weapon(frame)
    weapon_type, weapon_confidence = None, 0.0
    if detections:
        # Highest-confidence detection wins; MVP assumes one weapon in frame.
        detections.sort(key=lambda d: d[1], reverse=True)
        weapon_type, weapon_confidence, _bbox = detections[0]
        if weapon_confidence < confidence_threshold * 100:
            weapon_type, weapon_confidence = None, 0.0

    result = DetectionResult(
        user_id=user_id,
        user_name=user_name,
        face_confidence=face_confidence,
        weapon_type=weapon_type,
        weapon_confidence=weapon_confidence,
    )

    # --- Step 3: validation rules (spec §8/§11/§12/§13) ---
    if user_id is not None and weapon_type is not None:
        attendance_service.create_attendance(user_id)
        session_id = session_service.start_session(user_id, lane_id)
        result.session_id = session_id

        event_key = (user_id, weapon_type)
        now = time.time()
        cooldown_ok = (
            state["last_event_key"] != event_key
            or (now - state["last_event_time"]) >= event_cooldown_seconds
        )
        if cooldown_ok:
            event_service.log_weapon_event(
                session_id, user_id, weapon_type, weapon_confidence, camera_id, lane_id
            )
            state["last_event_key"] = event_key
            state["last_event_time"] = now
            result.event_logged = True

        result.message = f"User: {user_name} — Weapon: {weapon_type} ({weapon_confidence:.1f}%)"

    elif user_id is not None and weapon_type is None:
        result.message = f"User: {user_name} — Weapon: Not detected"

    elif user_id is None and weapon_type is not None:
        result.message = f"Weapon detected ({weapon_type}) — User not identified"

    else:
        result.message = "No user / weapon detected."

    return result
