import streamlit as st

from database.database import require_db_or_stop
from services import session_service
from utils.helpers import fmt_time

st.set_page_config(page_title="Sessions", page_icon="🏹", layout="wide")
require_db_or_stop()

st.title("Sessions")

status_filter = st.selectbox("Filter by status", ["All", "Active", "Completed"])
status = None if status_filter == "All" else status_filter
sessions = session_service.get_all_sessions(status=status)

if not sessions:
    st.caption("No sessions found.")
else:
    for s in sessions:
        cols = st.columns([2, 2, 2, 2, 2, 2])
        cols[0].write(f"SESSION-{s['session_id']:03d}")
        cols[1].write(s.get("name") or s.get("user_name") or "Unknown")
        cols[2].write(s["lane_id"])
        cols[3].write(fmt_time(s["start_time"]))
        cols[4].write(fmt_time(s["end_time"]) if s["end_time"] else "—")
        if s["status"] == "Active":
            if cols[5].button("End Session", key=f"end_{s['session_id']}"):
                session_service.end_session(s["session_id"])
                st.rerun()
        else:
            cols[5].write("Completed")
