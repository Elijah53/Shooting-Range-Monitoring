import streamlit as st

from database.database import execute, fetch_all, fetch_one, require_db_or_stop

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
require_db_or_stop()

st.title("Settings")



row = fetch_one("SELECT * FROM app_settings WHERE id = 1")

with st.form("settings_form"):
    confidence = st.slider(
        "Detection confidence threshold", 0.0, 1.0,
        float(row["detection_confidence_threshold"]) if row else 0.5, step=0.05,
    )
    cooldown = st.number_input(
        "Event cooldown (seconds)", min_value=1, max_value=120,
        value=row["event_cooldown_seconds"] if row else 7,
    )
    interval = st.number_input(
        "Face recognition interval (frames)", min_value=1, max_value=60,
        value=row["face_recognition_interval"] if row else 10,
    )
    camera_source = st.text_input(
        "Default camera source (index or stream URL)",
        value=row["camera_source"] if row else "0",
    )
    submitted = st.form_submit_button("Save Settings")

if submitted:
    execute(
        "UPDATE app_settings SET detection_confidence_threshold = %s, "
        "event_cooldown_seconds = %s, face_recognition_interval = %s, "
        "camera_source = %s WHERE id = 1",
        (confidence, cooldown, interval, camera_source),
    )
    st.success("Settings saved. Some changes take effect next time you start the camera.")


