"""
Entry point. Checks the database is reachable and initialized before
showing the dashboard; otherwise shows plain-English setup instructions
instead of a crash/traceback.
"""
import streamlit as st

from database.database import DatabaseUnavailableError, check_connection, init_db
from database.seed import seed_all

st.set_page_config(
    page_title="Shooting Range Attendance & Weapon Monitoring",
    page_icon="🎯",
    layout="wide",
)


def show_setup_instructions(error: str = ""):
    st.title("Setup required")
    st.error("The application could not connect to PostgreSQL.")
    if error:
        with st.expander("Technical details"):
            st.code(error)
    st.markdown(
        """
### To fix this:

1. Make sure PostgreSQL is installed and running locally.
2. Create a database, e.g.:
   ```sql
   CREATE DATABASE shooting_range;
   ```
3. Copy `.env.example` to `.env` in the project root and fill in your
   database credentials (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`,
   `DB_PASSWORD`, or a full `DATABASE_URL`).
4. Restart the app:
   ```bash
   streamlit run app.py
   ```
"""
    )


def main():
    if "db_ready" not in st.session_state:
        st.session_state["db_ready"] = check_connection()

    if not st.session_state["db_ready"]:
        show_setup_instructions()
        return

    if "db_initialized" not in st.session_state:
        try:
            init_db()
            seed_all()
            st.session_state["db_initialized"] = True
        except DatabaseUnavailableError as exc:
            show_setup_instructions(str(exc))
            return

    st.title("🎯 Shooting Range Attendance & Weapon Monitoring")
    st.markdown(
        "Use the sidebar to open **Dashboard**, **Check-In Station**, **Users**, "
        "**Sessions**, **Attendance**, **Weapon Events**, **Reports**, or **Settings**."
    )
    st.info(
        "This is a demo/academic system. Weapon detection identifies a "
        "weapon **type** only (e.g. Pistol) - it does not identify a "
        "specific inventory item or verify ownership."
    )


if __name__ == "__main__":
    main()
