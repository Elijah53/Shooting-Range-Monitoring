import time
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

# Initialize session state for user face capture
if "registration_capture_state" not in st.session_state:
    st.session_state["registration_capture_state"] = "idle"
if "registration_cam" not in st.session_state:
    st.session_state["registration_cam"] = None
if "registration_captured_frame" not in st.session_state:
    st.session_state["registration_captured_frame"] = None
if "pending_face_encoding" not in st.session_state:
    st.session_state["pending_face_encoding"] = None

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
    st.markdown("Register a new user, then capture their face.")

    if not face_lib.FACE_LIB_AVAILABLE:
        st.warning(
            "Face capture is unavailable because the `face_recognition` "
            "library is not installed. You can still create the user "
            "record and add a face later.\n\n"
            f"Details: {face_lib.IMPORT_ERROR}"
        )

    name = st.text_input("Full name", key="reg_user_name")
    phone = st.text_input("Phone number", key="reg_user_phone")

    capture_face = st.checkbox("Capture face now (uses webcam)", value=face_lib.FACE_LIB_AVAILABLE, key="reg_chk_face")

    if capture_face and face_lib.FACE_LIB_AVAILABLE:
        cap_state = st.session_state["registration_capture_state"]

        if cap_state == "idle":
            st.caption("Click below to start live camera preview before taking photo.")
            if st.button("▶ Start Camera Preview", type="primary", key="btn_start_preview"):
                try:
                    cam = Camera(settings.camera_source, target_fps=30)
                    cam.start()
                    st.session_state["registration_cam"] = cam
                    st.session_state["registration_capture_state"] = "previewing"
                    st.rerun()
                except CameraError as exc:
                    st.error(f"Camera Error: {exc}")

        elif cap_state == "previewing":
            cam = st.session_state.get("registration_cam")
            if cam is None or not cam.is_open:
                try:
                    cam = Camera(settings.camera_source, target_fps=30)
                    cam.start()
                    st.session_state["registration_cam"] = cam
                except CameraError as exc:
                    st.error(f"Camera Error: {exc}")
                    st.session_state["registration_capture_state"] = "idle"
                    cam = None

            if cam and cam.is_open:
                frame = cam.read_frame()
                if frame is not None:
                    preview_box = st.empty()
                    preview_box.image(frame, channels="RGB", caption="Live Preview — Center face and click 'Capture Photo'", width=480)

                    btn_c1, btn_c2 = st.columns([2, 2])
                    with btn_c1:
                        if st.button("📸 Capture Photo", type="primary", key="btn_capture_frame", use_container_width=True):
                            try:
                                encoding = face_lib.register_face(frame)
                                st.session_state["pending_face_encoding"] = encoding
                                st.session_state["registration_captured_frame"] = frame
                                st.session_state["registration_capture_state"] = "captured"
                                if cam:
                                    cam.stop()
                                st.session_state["registration_cam"] = None
                                st.rerun()
                            except face_lib.NoFaceDetectedError:
                                st.error("No face detected in the frame. Center your face and click Capture again.")
                            except face_lib.MultipleFacesDetectedError:
                                st.error("Multiple faces detected. Ensure only one person is in the frame.")
                    with btn_c2:
                        if st.button("⏹ Cancel Preview", key="btn_cancel_preview", use_container_width=True):
                            if cam:
                                cam.stop()
                            st.session_state["registration_cam"] = None
                            st.session_state["registration_capture_state"] = "idle"
                            st.rerun()

                    # Re-render next frame smoothly
                    time.sleep(0.04)
                    st.rerun()

        elif cap_state == "captured":
            captured_img = st.session_state.get("registration_captured_frame")
            if captured_img is not None:
                st.image(captured_img, channels="RGB", caption="Captured Face Confirmation Preview", width=360)
            st.success("✅ Face verified and biometric encoding captured. Click 'Save User' below.")

            if st.button("🔄 Retake Photo", key="btn_retake_photo"):
                st.session_state["pending_face_encoding"] = None
                st.session_state["registration_captured_frame"] = None
                try:
                    cam = Camera(settings.camera_source, target_fps=30)
                    cam.start()
                    st.session_state["registration_cam"] = cam
                    st.session_state["registration_capture_state"] = "previewing"
                    st.rerun()
                except CameraError as exc:
                    st.error(f"Camera Error: {exc}")
                    st.session_state["registration_capture_state"] = "idle"

    st.write("")
    if st.button("Save User", type="primary" if st.session_state.get("registration_capture_state") == "captured" else "secondary"):
        if not name.strip():
            st.error("Name is required.")
        else:
            # Clean up active camera if still running
            active_cam = st.session_state.get("registration_cam")
            if active_cam:
                try:
                    active_cam.stop()
                except Exception:
                    pass
                st.session_state["registration_cam"] = None

            encoding = st.session_state.pop("pending_face_encoding", None)
            user_id = user_service.register_user(name.strip(), phone.strip(), encoding)

            # Reset capture state
            st.session_state["registration_capture_state"] = "idle"
            st.session_state["registration_captured_frame"] = None

            st.success(f"User '{name}' registered successfully with ID {user_id}.")
            time.sleep(0.5)
            st.rerun()
