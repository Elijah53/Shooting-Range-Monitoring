import streamlit as st

from database.database import fetch_all, require_db_or_stop
from services import attendance_service, event_service, session_service
from utils.helpers import fmt_time

st.set_page_config(page_title="Dashboard", page_icon="🎯", layout="wide")
require_db_or_stop()

st.title("Dashboard")

col1, col2, col3, col4 = st.columns(4)
col1.metric("People Present", attendance_service.count_present_today())
col2.metric("Active Sessions", session_service.count_active_sessions())
col3.metric("Weapon Events Today", event_service.count_events_today())

cameras = fetch_all("SELECT * FROM cameras")
cameras_online = sum(1 for c in cameras if c["status"] == "Online")
col4.metric("Cameras Online", f"{cameras_online}/{len(cameras)}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Active Sessions")
    active_sessions = session_service.get_active_sessions()
    if active_sessions:
        st.dataframe(
            [
                {
                    "Session": f"SESSION-{s['session_id']:03d}",
                    "User": s["user_name"],
                    "Lane": s["lane_id"],
                    "Started": fmt_time(s["start_time"]),
                }
                for s in active_sessions
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No active sessions right now.")

with right:
    st.subheader("Recent Weapon Events")
    recent_events = event_service.get_events()[:5]
    if recent_events:
        st.dataframe(
            [
                {
                    "Time": fmt_time(e["detected_at"]),
                    "User": e.get("user_name") or "Unknown",
                    "Weapon": e["weapon_type"],
                    "Confidence": f"{e['confidence']:.1f}%",
                    "Camera": e["camera_id"] or "-",
                }
                for e in recent_events
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No weapon events logged yet.")

st.subheader("Recent Attendance")
recent_attendance = attendance_service.get_attendance()[:5]
if recent_attendance:
    st.dataframe(
        [
            {
                "User": a["user_name"],
                "Entry": fmt_time(a["entry_time"]),
                "Exit": fmt_time(a["exit_time"]),
                "Status": a["status"],
            }
            for a in recent_attendance
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.caption("No attendance recorded yet.")
