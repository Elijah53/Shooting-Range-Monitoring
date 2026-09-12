"""
pages/2_Live_Monitoring.py
--------------------------
State-Driven Front Desk Reception & Kiosk Terminal

Workflow:
1. Sequential Two-Step Check-In:
   - Step 1: Face Detection & Biometric Recognition (Pehle Face Detect)
   - Step 2: Weapon Safety Inspection & Classification (Than Weapon Detect)
   - When both verified -> Confirm Check-In & Start Range Session.
2. Manual Session End (Session End via Camera Removed):
   - Dedicated "Active Shooters on Range" panel with 1-click "End Session / Check-Out".
3. Flicker-Free Camera Streaming:
   - High-performance downscaled face processing + YOLO threat detection.
   - Non-flickering scoped live feed with stable action controls.
"""

from __future__ import annotations

import time
import cv2
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, date

st.set_page_config(
    page_title="Front Desk Kiosk — Shooting Range",
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
    require_db_or_stop()
    _imports_ok = True
except Exception as _import_err:
    _imports_ok = False
    _import_err_msg = str(_import_err)

if not _imports_ok:
    st.error(f"Initialization error: {_import_err_msg}")
    st.stop()


# ── Load Settings ─────────────────────────────────────────────────────────────
def _load_settings() -> dict:
    row = fetch_one("SELECT * FROM app_settings WHERE id=1")
    if row:
        return dict(row)
    from utils import config
    return {
        "face_match_threshold": config.FACE_MATCH_THRESHOLD,
        "detection_confidence_threshold": config.DETECTION_CONFIDENCE_THRESHOLD,
        "event_cooldown_seconds": config.EVENT_COOLDOWN_SECONDS,
        "face_recognition_interval": config.FACE_RECOGNITION_INTERVAL,
        "camera_source": config.CAMERA_SOURCE,
    }


settings = _load_settings()

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
    "auto_checkin": False,
    "last_toast_msg": "",
    "sim_mode": False,
}
for k, v in state_defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.kiosk_manager is None:
    st.session_state.kiosk_manager = KioskStateManager()

if st.session_state.pipeline is None:
    st.session_state.pipeline = DetectionPipeline(
        weapon_detector=get_weapon_detector(),
        face_match_threshold=float(settings.get("face_match_threshold", 0.60)),
        weapon_confidence_threshold=float(settings.get("detection_confidence_threshold", 0.40)),
        face_interval=int(settings.get("face_recognition_interval", 4)),
        weapon_interval=2,
    )


# ── Top Bar: Front Desk Header & Terminal Controls ─────────────────────────────
st.title("🏢 Front Desk Reception & Kiosk Terminal")
st.caption("Sequential Check-In Desk (Step 1: Face ID ➔ Step 2: Weapon Scan) | Manual Session End")

ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([2, 2, 2, 2])

with ctrl_col1:
    cameras = fetch_all("SELECT * FROM cameras ORDER BY camera_id")
    cam_options = {f"{r['camera_id']} ({r['lane_id']})": r for r in cameras} if cameras else {}
    if cam_options:
        sel_cam_label = st.selectbox("Counter Camera", list(cam_options.keys()), key="kiosk_cam_sel")
        st.session_state.desk_cam_id = cam_options[sel_cam_label]["camera_id"]
    else:
        st.selectbox("Counter Camera", ["CAM-01 (Front Desk)"], key="kiosk_cam_sel_def")
        st.session_state.desk_cam_id = "CAM-01"

with ctrl_col2:
    st.session_state.desk_lane = st.selectbox(
        "Assign Range Lane", ["Lane 1", "Lane 2", "Lane 3", "VIP Lane"], index=0
    )

with ctrl_col3:
    st.session_state.auto_checkin = st.toggle(
        "⚡ Auto-Confirm Check-In",
        value=st.session_state.auto_checkin,
        help="Automatically start session once Face + Weapon are verified",
    )

with ctrl_col4:
    st.write("") # vertical spacing
    if not st.session_state.camera_running:
        if st.button("▶ Start Camera Feed", type="primary", use_container_width=True):
            try:
                cam = Camera(settings.get("camera_source", "0"))
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
with st.expander("⚙️ Detection Sensitivity & Firearm Type Controls", expanded=False):
    c_cal1, c_cal2, c_cal3 = st.columns([2, 2, 2])
    with c_cal1:
        cur_w_thresh = float(st.session_state.pipeline.weapon_threshold if st.session_state.pipeline else 0.50)
        new_w_thresh = st.slider(
            "Weapon Confidence Cutoff", 0.20, 0.95, cur_w_thresh, step=0.05,
            help="Higher values reduce false alarms. 0.50 is recommended for general indoor lighting.",
            key="slider_wpn_thresh",
        )
        if st.session_state.pipeline:
            st.session_state.pipeline.weapon_threshold = new_w_thresh
    with c_cal2:
        st.session_state["weapon_type_override"] = st.selectbox(
            "Firearm Classification Mode",
            [
                "Auto (AI Gun Identifier: Glock 17, Beretta 92FS, AR-15)",
                "Force: Glock 17",
                "Force: Beretta 92FS",
                "Force: Colt M1911",
                "Force: Sig Sauer P320",
                "Force: Desert Eagle",
                "Force: Colt Python",
                "Force: AR-15 / M4",
                "Force: AK-47",
                "Force: Remington 870",
            ],
            key="sel_wpn_override",
            help="Auto identifies exact firearm model. You can also force a specific gun name.",
        )
    with c_cal3:
        model_options = {
            "Dedicated Pistol Detector (pistol_model.pt)": "model_data/pistol_model.pt",
            "Threat Gun Model (weapon_model.pt)": "model_data/weapon_model.pt",
            "CCTV Gun Model (cctv_gun_model.pt)": "model_data/cctv_gun_model.pt",
        }
        sel_model_label = st.selectbox(
            "Gun Detection Model Weights",
            list(model_options.keys()),
            index=0,
            key="sel_model_weights",
            help="Switch between specialized firearm models. Pistol.pt is recommended for handguns.",
        )
        chosen_path = model_options[sel_model_label]
        if st.session_state.pipeline and getattr(st.session_state.pipeline.detector, "_model_path", None) != chosen_path:
            from vision.weapon_detection import get_weapon_detector
            st.session_state.pipeline.detector = get_weapon_detector(chosen_path)
            st.toast(f"Switched model to {sel_model_label}")

st.divider()

# ── Helper Handlers for Actions ────────────────────────────────────────────────
def do_checkin():
    ctx = st.session_state.kiosk_manager.context
    if not ctx.user_id:
        st.error("No shooter identified.")
        return
    summary = TransactionManager.start_session(
        ctx=ctx,
        camera_id=st.session_state.desk_cam_id,
        lane_id=st.session_state.desk_lane,
        cooldown_cache=st.session_state.cooldown_cache,
        cooldown_seconds=int(settings.get("event_cooldown_seconds", 5)),
    )
    st.success(f"🎉 Check-In Successful! {summary['user_name']} assigned to {summary['lane_id']} with {summary['weapon_type']}.")


def do_reset():
    st.session_state.kiosk_manager.context.reset()
    st.session_state.kiosk_manager.face_stability_count = 0
    st.session_state.kiosk_manager.weapon_stability_count = 0


# ── Action Bar (Shows when ready or in progress) ───────────────────────────────
ctx_current = st.session_state.kiosk_manager.context

if ctx_current.current_state == KioskState.READY_FOR_CHECKIN:
    ready_banner, btn_act, btn_rst = st.columns([4, 2, 1])
    with ready_banner:
        st.success(
            f"🟢 **READY FOR CHECK-IN!** Verified Shooter: **{ctx_current.user_name}** | "
            f"Weapon: **{ctx_current.weapon_type or 'Firearm'}** ({pct(ctx_current.weapon_confidence)})"
        )
    with btn_act:
        if st.button("▶ Confirm Check-In & Enter", type="primary", use_container_width=True):
            do_checkin()
            st.rerun()
    with btn_rst:
        if st.button("🔄 Clear", use_container_width=True):
            do_reset()
            st.rerun()

elif ctx_current.current_state == KioskState.SESSION_COMPLETED and ctx_current.last_completed_summary:
    sumry = ctx_current.last_completed_summary
    st.balloons()
    st.success(
        f"✅ **CHECK-IN COMPLETE!** Shooter: **{sumry['user_name']}** | Lane: **{sumry['lane_id']}** | "
        f"Verified Weapon: **{sumry['weapon_type']}** | Time: **{sumry['time']}**"
    )


# ── Live Monitoring Viewport & Two-Step Verification Fragment ─────────────────

@st.fragment(run_every=0.15)
def live_feed_and_stages_fragment():
    v_col, s_col = st.columns([3, 2])

    kiosk_mgr: KioskStateManager = st.session_state.kiosk_manager
    ctx: KioskContext = kiosk_mgr.context

    # ── Left Column: Live Camera Video ──
    with v_col:
        st.markdown("##### 📹 Live Counter Feed")
        if not st.session_state.camera_running or not st.session_state.camera:
            st.info("📷 Reception Camera is in Standby. Click **▶ Start Camera Feed** above.")
        else:
            camera: Camera = st.session_state.camera
            pipeline: DetectionPipeline = st.session_state.pipeline

            if st.session_state.face_enc_cache is None:
                st.session_state.face_enc_cache = get_all_face_encodings()

            frame_rgb = camera.read_frame()
            if frame_rgb is None:
                st.warning("⚠️ Waiting for video stream from camera...")
            else:
                # Execute pure vision pipeline
                annotated_frame, det_result = pipeline.process_frame(
                    frame_rgb=frame_rgb,
                    face_encodings_cache=st.session_state.face_enc_cache,
                )

                # Apply Firearm Type Override if selected
                override_mode = st.session_state.get("weapon_type_override", "")
                if det_result.weapon_detected and override_mode.startswith("Force: "):
                    forced_w = override_mode.replace("Force: ", "").strip()
                    det_result.weapon_type = forced_w
                    det_result.weapon_category = forced_w


                # Update State Machine
                ctx = kiosk_mgr.update_from_detection(det_result)

                # Display video frame
                st.image(annotated_frame, channels="RGB", use_container_width=True)

                # If Auto-Checkin is enabled and ready, execute!
                if st.session_state.auto_checkin and ctx.current_state == KioskState.READY_FOR_CHECKIN:
                    TransactionManager.start_session(
                        ctx=ctx,
                        camera_id=st.session_state.desk_cam_id,
                        lane_id=st.session_state.desk_lane,
                        cooldown_cache=st.session_state.cooldown_cache,
                        cooldown_seconds=int(settings.get("event_cooldown_seconds", 5)),
                    )

    # ── Right Column: Two-Step Verification Cards ──
    with s_col:
        st.markdown("##### 🎯 Two-Step Verification Status")

        # ── SECTION 1: PEHLE FACE DETECT (Step 1) ─────────────────────────────
        st.markdown("###### 🪪 Step 1: Shooter Biometric Recognition")
        if ctx.current_state == KioskState.MULTIPLE_FACES_DETECTED:
            st.error("⚠️ **MULTIPLE FACES DETECTED**")
            st.caption("Please ensure only **one shooter** stands in front of counter.")
        elif ctx.current_state == KioskState.FACE_NOT_RECOGNIZED:
            st.warning("👤 **Unrecognized Person**")
            st.caption("Face detected but not registered. Please add user in Users tab.")
        elif ctx.face_confirmed and ctx.user_id is not None:
            if ctx.current_state == KioskState.SESSION_ACTIVE:
                st.warning(f"⚠️ **Shooter Already Inside Range:** **{ctx.user_name}**")
                st.caption(f"Session #{ctx.active_session_id} | In: {ctx.entry_time} ({ctx.duration_str} ago)")
                st.info("👉 To check-out this shooter, click 'End Session' in the table below.")
            else:
                st.success(f"✅ **Step 1 Confirmed:** **{ctx.user_name}** (Match: {pct(ctx.face_confidence)})")
                st.caption(f"Shooter ID: #{ctx.user_id} | Biometrics Verified")
        else:
            st.info("⏳ **Searching for shooter at counter...**")
            st.caption("Please stand facing the camera.")

        st.markdown("---")

        # ── SECTION 2: THAN WEAPON DETECT (Step 2) ────────────────────────────
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
                    st.caption(f"Specs: {ctx.weapon_details}")
            else:
                st.warning("⏳ **Action Required: Please present firearm to camera.**")
                st.caption("Hold weapon in view of camera for safety verification.")

        # Summary State Indicator
        if ctx.current_state == KioskState.READY_FOR_CHECKIN:
            st.success("🟢 **All Steps Verified — Ready for Check-In!**")
        elif ctx.face_confirmed and ctx.current_state != KioskState.SESSION_ACTIVE:
            st.info("🟡 **Step 1 Complete** ➔ Waiting for weapon verification")


# Call the streaming fragment
live_feed_and_stages_fragment()


# ── MANUAL SESSION END & ACTIVE SHOOTERS PANEL ────────────────────────────────
st.divider()

st.subheader("🎯 Active Shooters on Range (Manual Check-Out)")
st.caption("Session end via camera is disabled. Desk operator clicks 'End Session' below to check out shooters.")

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
