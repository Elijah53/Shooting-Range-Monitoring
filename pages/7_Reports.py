from datetime import date, timedelta

import pandas as pd
import streamlit as st

from database.database import fetch_all, require_db_or_stop
from services import attendance_service, event_service, session_service, user_service
from utils.helpers import fmt_time

st.set_page_config(page_title="Reports", page_icon="📊", layout="wide")
require_db_or_stop()

st.title("Reports")

tab_attendance, tab_sessions, tab_weapons, tab_user_history = st.tabs(
    ["Daily Attendance", "Session Statistics", "Weapon Detection Stats", "User History"]
)

with tab_attendance:
    rows = fetch_all(
        "SELECT entry_time::date AS day, COUNT(*) AS visits "
        "FROM attendance GROUP BY entry_time::date ORDER BY day DESC"
    )
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["day", "visits"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    if not df.empty:
        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="daily_attendance.csv",
            mime="text/csv",
        )

with tab_sessions:
    rows = fetch_all(
        "SELECT COUNT(*) AS total_sessions, "
        "AVG(EXTRACT(EPOCH FROM (end_time - start_time))/60) AS avg_minutes "
        "FROM sessions WHERE status = 'Completed'"
    )
    total = rows[0]["total_sessions"] if rows else 0
    avg_minutes = rows[0]["avg_minutes"] if rows and rows[0]["avg_minutes"] else 0
    c1, c2 = st.columns(2)
    c1.metric("Completed Sessions", total)
    c2.metric("Average Duration (min)", f"{avg_minutes:.1f}" if avg_minutes else "0")

    all_sessions = session_service.get_all_sessions()
    df = pd.DataFrame(
        [
            {
                "Session": f"SESSION-{s['session_id']:03d}",
                "User": s.get("name") or s.get("user_name") or "Unknown",
                "Lane": s["lane_id"],
                "Start": fmt_time(s["start_time"]),
                "End": fmt_time(s["end_time"]),
                "Status": s["status"],
            }
            for s in all_sessions
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    if not df.empty:
        st.download_button(
            "Download CSV", df.to_csv(index=False).encode("utf-8"),
            file_name="sessions.csv", mime="text/csv",
        )

with tab_weapons:
    rows = fetch_all(
        "SELECT weapon_type, COUNT(*) AS detections, ROUND(AVG(confidence), 1) AS avg_confidence "
        "FROM weapon_events GROUP BY weapon_type ORDER BY detections DESC"
    )
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["weapon_type", "detections", "avg_confidence"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    if not df.empty:
        st.download_button(
            "Download CSV", df.to_csv(index=False).encode("utf-8"),
            file_name="weapon_stats.csv", mime="text/csv",
        )

with tab_user_history:
    users = user_service.get_all_users()
    user_options = {u.name: u.user_id for u in users}
    if user_options:
        chosen = st.selectbox("Select user", list(user_options.keys()))
        uid = user_options[chosen]

        st.markdown("**Attendance**")
        att = attendance_service.get_attendance(user_id=uid)
        st.dataframe(
            [{"Entry": fmt_time(a["entry_time"]), "Exit": fmt_time(a["exit_time"]), "Status": a["status"]} for a in att],
            use_container_width=True, hide_index=True,
        )

        st.markdown("**Sessions**")
        sess = session_service.get_all_sessions(user_id=uid)
        st.dataframe(
            [{"Session": f"SESSION-{s['session_id']:03d}", "Lane": s["lane_id"], "Status": s["status"]} for s in sess],
            use_container_width=True, hide_index=True,
        )

        st.markdown("**Weapon Events**")
        evs = event_service.get_events(user_id=uid)
        st.dataframe(
            [{"Time": fmt_time(e["detected_at"]), "Weapon": e["weapon_type"], "Confidence": f"{e['confidence']:.1f}%"} for e in evs],
            use_container_width=True, hide_index=True,
        )
    else:
        st.caption("No users registered yet.")
