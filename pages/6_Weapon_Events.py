from datetime import date, timedelta

import streamlit as st

from database.database import fetch_all, require_db_or_stop
from services import event_service
from utils.helpers import fmt_time

st.set_page_config(page_title="Weapon Events", page_icon="🔫", layout="wide")
require_db_or_stop()

st.title("Weapon Events")

c1, c2, c3 = st.columns(3)
date_from = c1.date_input("From", value=date.today() - timedelta(days=7))
date_to = c2.date_input("To", value=date.today())

weapon_types = ["All"] + sorted({row["weapon_type"] for row in fetch_all("SELECT DISTINCT weapon_type FROM weapon_events")})
weapon_filter = c3.selectbox("Weapon type", weapon_types)
weapon_type = None if weapon_filter == "All" else weapon_filter

events = event_service.get_events(date_from=date_from, date_to=date_to, weapon_type=weapon_type)

if not events:
    st.caption("No weapon events in this range.")
else:
    st.dataframe(
        [
            {
                "Time": fmt_time(e["detected_at"]),
                "User": e.get("name") or e.get("user_name") or "Unidentified",
                "Weapon": e["weapon_type"],
                "Confidence": f"{e['confidence']:.1f}%",
                "Camera": e["camera_id"] or "-",
                "Lane": e["lane_id"] or "-",
            }
            for e in events
        ],
        use_container_width=True,
        hide_index=True,
    )
