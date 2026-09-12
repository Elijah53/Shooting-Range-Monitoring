from datetime import date, timedelta

import streamlit as st

from database.database import require_db_or_stop
from services import attendance_service
from utils.helpers import fmt_time

st.set_page_config(page_title="Attendance", page_icon="🗓️", layout="wide")
require_db_or_stop()

st.title("Attendance")

c1, c2 = st.columns(2)
date_from = c1.date_input("From", value=date.today() - timedelta(days=7))
date_to = c2.date_input("To", value=date.today())

records = attendance_service.get_attendance(date_from=date_from, date_to=date_to)

if not records:
    st.caption("No attendance records in this range.")
else:
    st.dataframe(
        [
            {
                "User": r.get("name") or r.get("user_name") or "Unknown",
                "Entry Time": fmt_time(r["entry_time"]),
                "Exit Time": fmt_time(r["exit_time"]),
                "Status": r["status"],
            }
            for r in records
        ],
        use_container_width=True,
        hide_index=True,
    )
