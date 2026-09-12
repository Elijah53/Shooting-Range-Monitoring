import streamlit as st

from database.database import require_db_or_stop
from services import user_service
from utils.config import load_settings
from utils.helpers import fmt_time
from vision import face_recognition as face_lib
from vision.camera import Camera, CameraError

st.set_page_config(page_title="Users", page_icon="👤", layout="wide")
require_db_or_stop()
settings = load_settings()

st.title("Users")

tab_list, tab_register = st.tabs(["View / Manage Users", "Register User"])

with tab_list:
    query = st.text_input("Search by name")
    users = user_service.search_users(query) if query else user_service.get_all_users()

    if not users:
        st.caption("No users found.")
    for u in users:
        with st.expander(f"{u.name}  ·  {u.status}  ·  {'Face on file' if u.has_face else 'No face captured'}"):
            c1, c2 = st.columns(2)
            new_name = c1.text_input("Name", value=u.name, key=f"name_{u.user_id}")
            new_phone = c2.text_input("Phone", value=u.phone or "", key=f"phone_{u.user_id}")
            st.caption(f"Registered: {fmt_time(u.registration_date)}")

            b1, b2, b3 = st.columns(3)
            if b1.button("Save changes", key=f"save_{u.user_id}"):
                user_service.update_user(u.user_id, new_name, new_phone)
                st.success("Updated.")
                st.rerun()
            if u.status == "Active":
                if b2.button("Deactivate", key=f"deact_{u.user_id}"):
                    user_service.deactivate_user(u.user_id)
                    st.rerun()
            else:
                if b2.button("Activate", key=f"act_{u.user_id}"):
                    user_service.activate_user(u.user_id)
                    st.rerun()

with tab_register:
    st.markdown("Register a new user, then capture their face separately.")

    if not face_lib.FACE_LIB_AVAILABLE:
        st.warning(
            "Face capture is unavailable because the `face_recognition` "
            "library is not installed. You can still create the user "
            "record and add a face later.\n\n"
            f"Details: {face_lib.IMPORT_ERROR}"
        )

    name = st.text_input("Full name")
    phone = st.text_input("Phone number")

    capture_face = st.checkbox("Capture face now (uses webcam)", value=face_lib.FACE_LIB_AVAILABLE)

    captured_encoding = None
    if capture_face and face_lib.FACE_LIB_AVAILABLE:
        if st.button("📷 Capture from webcam"):
            try:
                cam = Camera(settings.camera_source)
                cam.start()
                frame = cam.read_frame()
                cam.stop()
                try:
                    encoding = face_lib.register_face(frame)
                    st.session_state["pending_face_encoding"] = encoding
                    st.image(frame[:, :, ::-1], caption="Captured frame", width=300)
                    st.success("Face captured. Review the preview, then click Save User below.")
                except face_lib.NoFaceDetectedError:
                    st.error("No face detected in the captured frame. Try again.")
                except face_lib.MultipleFacesDetectedError:
                    st.error("Multiple faces detected. Make sure only one person is in frame.")
            except CameraError as exc:
                st.error(str(exc))

    if st.button("Save User"):
        if not name.strip():
            st.error("Name is required.")
        else:
            encoding = st.session_state.pop("pending_face_encoding", None)
            user_id = user_service.register_user(name.strip(), phone.strip(), encoding)
            st.success(f"User '{name}' registered with ID {user_id}.")
            st.rerun()
