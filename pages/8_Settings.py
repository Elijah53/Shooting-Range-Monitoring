import streamlit as st

from database.database import execute, fetch_all, fetch_one, require_db_or_stop

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
require_db_or_stop()

st.title("Settings")

st.markdown(
    "These values are stored in the database (`app_settings` table) so "
    "they can be changed here without editing `.env` or restarting. "
    "`.env` values are still used as the *initial* defaults on first run."
)

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

st.divider()
st.subheader("Cameras / Lanes")

cameras = fetch_all("SELECT * FROM cameras ORDER BY camera_id")
st.dataframe(
    [{"Camera": c["camera_id"], "Lane": c["lane_id"], "Status": c["status"]} for c in cameras],
    use_container_width=True, hide_index=True,
)

with st.expander("Add camera / lane"):
    new_cam_id = st.text_input("Camera ID (e.g. CAM-03)")
    new_lane = st.text_input("Lane (e.g. Lane 3)")
    if st.button("Add Camera"):
        if new_cam_id and new_lane:
            execute(
                "INSERT INTO cameras (camera_id, lane_id, status) VALUES (%s, %s, 'Online')",
                (new_cam_id, new_lane),
            )
            st.success("Camera added.")
            st.rerun()
        else:
            st.error("Both fields are required.")
