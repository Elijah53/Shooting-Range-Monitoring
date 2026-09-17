"""
pages/2_Live_Monitoring.py
--------------------------
State-Driven Front Desk Reception & Kiosk Terminal

Workflow:
1. Sequential Two-Step Check-In:
   - Step 1: Shooter Biometric Recognition
   - Step 2: Weapon Safety Inspection (Multi-Class YOLO)
   - When both verified -> Confirm Check-In & Start Range Session.
2. Manual Session End:
   - "Active Shooters on Range" panel with 1-click "End Session / Check-Out".
3. Flicker-Free Camera Streaming:
   - Dedicated background thread video capture driver.
   - Persistent Streamlit container rendering without timer-based fragment reruns.
   - Hardware exposure & FPS locking.
"""

from __future__ import annotations

import time
import cv2
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, date

st.set_page_config(
    page_title="Check-In Station — Shooting Range",
    page_icon="🏢",
    layout="wide",
)

# ── Graceful Imports ──────────────────────────────────────────────────────────
try:
    from database.database import fetch_all, fetch_one, fetch_scalar, require_db_or_stop
    from vision.camera import Camera, CameraError
    from vision.detection_pipeline import DetectionPipeline
    from vision.weapon_detection import get_weapon_detector
    from services.kiosk_service import KioskStateManager, TransactionManager
    from services.user_service import get_all_face_encodings
    from services import attendance_service, session_service, event_service
    from models.kiosk_state import KioskState, TransactionType, KioskContext
    from utils.helpers import format_dt, pct, duration_str
    from utils import config
    require_db_or_stop()
    _imports_ok = True
except Exception as _import_err:
    _imports_ok = False
    _import_err_msg = str(_import_err)

if not _imports_ok:
    st.error(f"Initialization error: {_import_err_msg}")
    st.stop()


# ── Load Live Settings ────────────────────────────────────────────────────────
def load_live_settings():
    row = fetch_one("SELECT * FROM app_settings WHERE id = 1")
    base = config.load_settings()  # .env defaults as fallback
    if not row:
        return base
    return base.__class__(
        **{
            **base.__dict__,
            "detection_confidence_threshold": float(row["detection_confidence_threshold"]),
            "event_cooldown_seconds": int(row["event_cooldown_seconds"]),
            "face_recognition_interval": int(row["face_recognition_interval"]),
            "camera_source": str(row["camera_source"]),
        }
    )


settings = load_live_settings()

# ── Session State Initialization ──────────────────────────────────────────────
state_defaults = {
    "camera": None,
    "camera_running": False,
    "pipeline": None,
    "kiosk_manager": None,
    "cooldown_cache": {},
    "face_enc_cache": None,
    "desk_lane": "Lane 1",
    "desk_cam_id": "CAM-01",
    "auto_checkin": True,
}
for k, v in state_defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.kiosk_manager is None:
    st.session_state.kiosk_manager = KioskStateManager()

target_model_path = config.WEAPON_MODEL_PATH
if (
    st.session_state.pipeline is None
    or getattr(st.session_state.pipeline.detector, "_model_path", None) != target_model_path
):
    st.session_state.pipeline = DetectionPipeline(
        weapon_detector=get_weapon_detector(target_model_path),
        face_match_threshold=float(settings.face_match_threshold),
        weapon_confidence_threshold=float(settings.detection_confidence_threshold),
        face_interval=int(settings.face_recognition_interval),
        weapon_interval=1,
    )


# ── Helper Handlers for Actions ────────────────────────────────────────────────
def do_checkin():
    ctx = st.session_state.kiosk_manager.context
    if not ctx.user_id:
        return None
    summary = TransactionManager.start_session(
        ctx=ctx,
        camera_id=st.session_state.desk_cam_id,
        lane_id=st.session_state.desk_lane,
        cooldown_cache=st.session_state.cooldown_cache,
        cooldown_seconds=int(settings.event_cooldown_seconds),
    )
    return summary


def do_reset():
    st.session_state.kiosk_manager.context.reset()
    st.session_state.kiosk_manager.face_stability_count = 0
    st.session_state.kiosk_manager.weapon_stability_count = 0


# ── Top Bar: Check-In Station Header & Terminal Controls ──────────────────────
st.title("🏢 Check-In Station")
st.caption("Reception Desk (Step 1: Face ID ➔ Step 2: Weapon Scan) | Atomic Transactions")

ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([2, 2, 2, 2])

with ctrl_col1:
    cameras = fetch_all("SELECT * FROM cameras ORDER BY camera_id")
    cam_options = {f"{r['camera_id']} ({r['lane_id']})": r for r in cameras} if cameras else {}
    if cam_options:
        sel_cam_label = st.selectbox("Counter Camera", list(cam_options.keys()), key="kiosk_cam_sel")
        st.session_state.desk_cam_id = cam_options[sel_cam_label]["camera_id"]
    else:
        st.selectbox("Counter Camera", ["CAM-01 (Reception)"], key="kiosk_cam_sel_def")
        st.session_state.desk_cam_id = "CAM-01"

with ctrl_col2:
    st.session_state.desk_lane = st.selectbox(
        "Assign Range Lane", ["Lane 1", "Lane 2", "Lane 3", "VIP Lane"], index=0
    )

with ctrl_col3:
    st.session_state.auto_checkin = st.toggle(
        "⚡ Auto-Confirm Check-In",
        value=st.session_state.auto_checkin,
        help="Automatically execute atomic check-in transaction once Face + Weapon are verified",
    )

with ctrl_col4:
    st.write("")  # vertical spacing
    if not st.session_state.camera_running:
        if st.button("▶ Start Camera Feed", type="primary", use_container_width=True):
            try:
                cam = Camera(settings.camera_source, target_fps=30)
                cam.start()
                st.session_state.camera = cam
                st.session_state.camera_running = True
                st.session_state.kiosk_manager.context.reset()
                st.session_state.face_enc_cache = get_all_face_encodings()
                st.rerun()
            except CameraError as e:
                st.error(f"📵 Camera Error: {e}")
    else:
        if st.button("⏹ Stop Camera Feed", type="secondary", use_container_width=True):
            if st.session_state.camera:
                try:
                    st.session_state.camera.stop()
                except Exception:
                    pass
            st.session_state.camera = None
            st.session_state.camera_running = False
            st.session_state.kiosk_manager.context.reset()
            st.rerun()


# ── Calibration & Sensitivity Controls ────────────────────────────────────────
with st.expander("⚙️ Detection Sensitivity & Firearm Model Settings", expanded=False):
    c_cal1, c_cal2 = st.columns([3, 3])
    with c_cal1:
        cur_w_thresh = float(st.session_state.pipeline.weapon_threshold if st.session_state.pipeline else settings.detection_confidence_threshold)
        new_w_thresh = st.slider(
            "Firearm Confidence Cutoff", 0.30, 0.95, cur_w_thresh, step=0.05,
            help="Confidence threshold for YOLO firearm detection (Pistols / Rifles). Increase to eliminate false positives on everyday objects.",
            key="slider_wpn_thresh",
        )
        if st.session_state.pipeline:
            st.session_state.pipeline.weapon_threshold = new_w_thresh
            if hasattr(st.session_state.pipeline.detector, "_confidence_threshold"):
                st.session_state.pipeline.detector._confidence_threshold = new_w_thresh

    with c_cal2:
        st.markdown("**🎯 Active Firearm Model**")
        st.info("🛡️ **YOLO Multi-Firearm Detector** (`model_data/multi_weapon_model.pt`)\n\n*Optimized for shooting ranges (Pistols, Rifles, Long Guns).*")

st.divider()


# ── Status Card Renderer (Pure Component) ─────────────────────────────────────
def render_status_card(container, ctx: KioskContext):
    """Render the status cards inside a persistent Streamlit container."""
    with container.container():
        st.markdown("##### 🎯 Two-Step Verification Status")
        st.caption(f"Detection confidence cutoff: {settings.detection_confidence_threshold * 100:.0f}%")

        # ── Step 1: Face ID Card ──
        st.markdown("###### 🪪 Step 1: Shooter Biometric Recognition")
        if ctx.current_state == KioskState.MULTIPLE_FACES_DETECTED:
            st.error("⚠️ **MULTIPLE FACES DETECTED**\nPlease ensure only **one shooter** stands in front of counter.")
        elif ctx.current_state == KioskState.FACE_NOT_RECOGNIZED:
            st.warning("👤 **Unrecognized Person**\nFace detected but not registered. Please add user in Users tab.")
        elif ctx.face_confirmed and ctx.user_id is not None:
            if ctx.current_state == KioskState.SESSION_ACTIVE:
                st.warning(f"⚠️ **Shooter Already Inside Range:** **{ctx.user_name}**")
                st.caption(f"Session #{ctx.active_session_id} | In: {ctx.entry_time} ({ctx.duration_str} ago)")
            else:
                st.success(f"✅ **Step 1 Confirmed:** **{ctx.user_name}** (Match: {pct(ctx.face_confidence)})")
                st.caption(f"Shooter ID: #{ctx.user_id} | Biometrics Verified")
        else:
            st.info("⏳ **Searching for shooter at counter...**\nPlease stand facing the camera.")

        st.markdown("---")

        # ── Step 2: Weapon Verification Card ──
        st.markdown("###### 🔫 Step 2: Weapon Safety Inspection")
        if not ctx.face_confirmed:
            st.markdown(
                "<div style='padding: 12px; border: 1px dashed #777; border-radius: 8px; color: #888;'>"
                "🔒 <i>Locked — Waiting for Step 1 (Face Identification)</i></div>",
                unsafe_allow_html=True,
            )
        elif ctx.current_state == KioskState.SESSION_ACTIVE:
            st.caption("Weapon verification paused while shooter has active session.")
        else:
            if ctx.weapon_type is not None:
                st.success(f"✅ **Step 2 Verified:** **{ctx.weapon_type}** ({pct(ctx.weapon_confidence)})")
                if ctx.weapon_details:
                    st.caption(f"Category: {ctx.weapon_category} | {ctx.weapon_details}")
            else:
                st.warning("⏳ **Action Required: Please present firearm to camera.**")
                st.caption("Hold weapon in view of camera for safety verification.")

        # Overall Status Banner
        if ctx.current_state == KioskState.READY_FOR_CHECKIN:
            st.success("🟢 **All Steps Verified — Ready for Check-In!**")
        elif ctx.current_state == KioskState.SESSION_COMPLETED and ctx.last_completed_summary:
            sumry = ctx.last_completed_summary
            st.success(
                f"🎉 **CHECK-IN COMPLETE!** Shooter: **{sumry['user_name']}** | Lane: **{sumry['lane_id']}** | "
                f"Weapon: **{sumry['weapon_type']}**"
            )


# ── Persistent Video & Status Layout Containers ──────────────────────────────
feed_col, status_col = st.columns([3, 2])

with feed_col:
    video_container = st.empty()

with status_col:
    status_container = st.empty()
    action_container = st.empty()


# ── Action Buttons Container ──────────────────────────────────────────────────
def render_action_bar(container, ctx: KioskContext):
    with container.container():
        if ctx.current_state == KioskState.READY_FOR_CHECKIN:
            b_col1, b_col2 = st.columns([2, 1])
            with b_col1:
                if st.button("▶ Confirm Check-In & Enter", type="primary", use_container_width=True, key="btn_confirm_checkin"):
                    do_checkin()
                    st.rerun()
            with b_col2:
                if st.button("🔄 Clear", use_container_width=True, key="btn_clear_kiosk"):
                    do_reset()
                    st.rerun()


# ── Persistent Non-Flickering Video Stream Loop ──────────────────────────────
if not st.session_state.camera_running or not st.session_state.camera:
    video_container.info("📷 Reception Camera is in Standby. Click **▶ Start Camera Feed** above.")
    render_status_card(status_container, st.session_state.kiosk_manager.context)
else:
    camera: Camera = st.session_state.camera
    pipeline: DetectionPipeline = st.session_state.pipeline
    kiosk_mgr: KioskStateManager = st.session_state.kiosk_manager

    if st.session_state.face_enc_cache is None:
        st.session_state.face_enc_cache = get_all_face_encodings()

    # Initial frame check
    frame_rgb = camera.read_frame()
    if frame_rgb is None:
        video_container.warning("⚠️ Waiting for video stream from threaded capture driver...")
        render_status_card(status_container, kiosk_mgr.context)
    else:
        # Continuous streaming loop updating persistent placeholders without page remounts
        # Runs smoothly at target frame rate
        annotated_frame, det_result = pipeline.process_frame(
            frame_rgb=frame_rgb,
            face_encodings_cache=st.session_state.face_enc_cache,
        )
        ctx = kiosk_mgr.update_from_detection(det_result)
        video_container.image(annotated_frame, channels="RGB", width="stretch")
        render_status_card(status_container, ctx)
        render_action_bar(action_container, ctx)

        if ctx.current_state == KioskState.READY_FOR_CHECKIN:
            summary = do_checkin()
            if summary:
                st.toast(f"🎯 Range Session Active: {summary['user_name']} ({summary['weapon_type']}) on {st.session_state.desk_lane}!", icon="🔫")
            st.rerun()

        # Stream smoothly until Streamlit triggers a user interaction
        # We loop with a tiny sleep to keep frame rendering snappy and flicker-free
        for _ in range(25):  # Process batch of frames smoothly per script cycle
            if not st.session_state.camera_running or not camera.is_open:
                break
            f_rgb = camera.read_frame()
            if f_rgb is not None:
                annotated_f, d_res = pipeline.process_frame(
                    frame_rgb=f_rgb,
                    face_encodings_cache=st.session_state.face_enc_cache,
                )
                ctx = kiosk_mgr.update_from_detection(d_res)
                video_container.image(annotated_f, channels="RGB", width="stretch")
                render_status_card(status_container, ctx)
                if ctx.current_state == KioskState.READY_FOR_CHECKIN:
                    summary = do_checkin()
                    if summary:
                        st.toast(f"🎯 Range Session Active: {summary['user_name']} ({summary['weapon_type']}) on {st.session_state.desk_lane}!", icon="🔫")
                    st.rerun()
            time.sleep(0.035)

        # Trigger automatic smooth rerun to continue live stream if camera still active
        if st.session_state.camera_running:
            time.sleep(0.01)
            st.rerun()


# ── MANUAL SESSION END & ACTIVE SHOOTERS PANEL ────────────────────────────────
st.divider()

st.subheader("🎯 Active Shooters on Range (Manual Check-Out)")
st.caption("Desk operator clicks 'End Session' below to check out shooters in an atomic transaction.")

active_sessions = fetch_all(
    """
    SELECT 
        s.session_id,
        s.user_id,
        u.name AS user_name,
        s.lane_id,
        s.start_time,
        s.status,
        (
            SELECT we.weapon_type 
            FROM weapon_events we 
            WHERE we.session_id = s.session_id 
            ORDER BY we.detected_at DESC 
            LIMIT 1
        ) AS carried_weapon,
        a.attendance_id,
        a.entry_time
    FROM sessions s
    JOIN users u ON u.user_id = s.user_id
    LEFT JOIN attendance a ON a.user_id = s.user_id AND a.status = 'Active'
    WHERE s.status = 'Active'
    ORDER BY s.start_time DESC
    """
)

if active_sessions:
    for sess in active_sessions:
        row_c1, row_c2, row_c3, row_c4, row_c5 = st.columns([3, 2, 2, 2, 2])
        with row_c1:
            st.markdown(f"**👤 {sess['user_name']}**")
            st.caption(f"Session #{sess['session_id']} | ID: #{sess['user_id']}")
        with row_c2:
            st.markdown(f"**🔫 {sess['carried_weapon'] or 'Standard Firearm'}**")
            st.caption(f"Lane: {sess['lane_id']}")
        with row_c3:
            in_time_str = format_dt(sess["start_time"], "%I:%M %p")
            st.markdown(f"**🕒 In:** {in_time_str}")
        with row_c4:
            dur = duration_str(sess["start_time"], None)
            st.markdown(f"**⏱️ Duration:** {dur}")
        with row_c5:
            if st.button(
                "🏁 End Session",
                key=f"btn_end_sess_{sess['session_id']}",
                type="primary",
                use_container_width=True,
            ):
                out = TransactionManager.end_session_manually(
                    session_id=sess["session_id"],
                    user_id=sess["user_id"],
                )
                dur_m = out.get("duration_minutes", 1) if out else 1
                st.toast(f"🏁 Session #{sess['session_id']} closed for {sess['user_name']} ({dur_m} mins).", icon="🚪")
                time.sleep(0.3)
                st.rerun()
        st.markdown("<hr style='margin:4px 0px; border-color:#333;'/>", unsafe_allow_html=True)
else:
    st.info("🟢 No active sessions on the shooting range right now.")


# ── AREA 3: TODAY'S COUNTER ATTENDANCE & WEAPON REGISTER ──────────────────────
st.divider()
st.subheader("📋 Today's Counter Attendance & Weapon Register")

sql_today = """
    SELECT 
        a.attendance_id,
        a.user_id,
        u.name AS user_name,
        a.entry_time,
        a.exit_time,
        a.status AS attendance_status,
        (
            SELECT we.weapon_type 
            FROM weapon_events we 
            WHERE we.user_id = a.user_id 
              AND we.detected_at::date = a.entry_time::date
            ORDER BY we.detected_at DESC 
            LIMIT 1
        ) AS weapon_model,
        (
            SELECT s.session_id 
            FROM sessions s 
            WHERE s.user_id = a.user_id 
              AND s.start_time::date = a.entry_time::date
            ORDER BY s.start_time DESC 
            LIMIT 1
        ) AS session_id
    FROM attendance a
    JOIN users u ON u.user_id = a.user_id
    WHERE a.entry_time::date = %s
    ORDER BY a.entry_time DESC
    LIMIT 15
"""
today_records = fetch_all(sql_today, (date.today(),))

if today_records:
    desk_rows = []
    for r in today_records:
        entry_s = format_dt(r["entry_time"], "%I:%M %p")
        exit_s = format_dt(r.get("exit_time"), "%I:%M %p") if r.get("exit_time") else "— (Inside)"
        dur_s = duration_str(r["entry_time"], r.get("exit_time"))
        status_txt = "🟢 Inside Range" if r["attendance_status"] == "Active" else "🏁 Checked Out"
        wpn_model = r["weapon_model"] or "Firearm"
        sess_str = f"#{r['session_id']}" if r.get("session_id") else "—"

        desk_rows.append({
            "Shooter Name": r["user_name"],
            "🔫 Verified Weapon": wpn_model,
            "Session": sess_str,
            "Entry Time": entry_s,
            "Exit Time": exit_s,
            "Total Duration": dur_s,
            "Counter Status": status_txt,
        })
    st.dataframe(pd.DataFrame(desk_rows), use_container_width=True, hide_index=True)
else:
    st.info("No check-ins recorded yet today.")
