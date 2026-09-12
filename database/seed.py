"""
database/seed.py
----------------
Inserts demo / sample data into an empty database.

All inserts are guarded by a COUNT(*) check — running this script
multiple times is safe (idempotent).

DEMO DATA — clearly labelled for academic demonstration purposes.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from database.database import execute, fetch_scalar


def _table_empty(table: str) -> bool:
    count = fetch_scalar(f"SELECT COUNT(*) FROM {table}")
    return (count or 0) == 0


def seed() -> None:
    """Insert demo data only if the tables are empty."""

    # ── Users ─────────────────────────────────────────────────────────────────
    if _table_empty("users"):
        print("[seed] Inserting demo users …")
        demo_users = [
            ("Rahul Sharma", "9876543210"),
            ("Amit Kumar",   "9123456789"),
            ("Neha Singh",   "9000011112"),
        ]
        for name, phone in demo_users:
            execute(
                "INSERT INTO users (name, phone, status) VALUES (%s, %s, 'Active')",
                (name, phone),
            )
        print("[seed] ✓ Users seeded (face_encoding left NULL — register via UI).")

    # ── Weapons ───────────────────────────────────────────────────────────────
    if _table_empty("weapons"):
        print("[seed] Inserting demo weapons …")
        demo_weapons = [
            ("WPN-001", "Pistol",  "Available"),
            ("WPN-002", "Rifle",   "Available"),
            ("WPN-003", "Pistol",  "Available"),
        ]
        for wid, wtype, wstatus in demo_weapons:
            execute(
                "INSERT INTO weapons (weapon_id, weapon_type, status) VALUES (%s, %s, %s)",
                (wid, wtype, wstatus),
            )
        print("[seed] ✓ Weapons seeded.")

    # ── Cameras ───────────────────────────────────────────────────────────────
    if _table_empty("cameras"):
        print("[seed] Inserting demo cameras …")
        demo_cameras = [
            ("CAM-01", "Lane 1", "Online"),
            ("CAM-02", "Lane 2", "Online"),
        ]
        for cid, lane, cstatus in demo_cameras:
            execute(
                "INSERT INTO cameras (camera_id, lane_id, status) VALUES (%s, %s, %s)",
                (cid, lane, cstatus),
            )
        print("[seed] ✓ Cameras seeded.")

    # ── Historical records (demo / sample) ────────────────────────────────────
    # These give the Dashboard and Reports pages non-empty data on first run.
    if _table_empty("attendance"):
        print("[seed] Inserting demo attendance records …")
        user1_id = fetch_scalar("SELECT user_id FROM users WHERE name='Rahul Sharma' LIMIT 1")
        user2_id = fetch_scalar("SELECT user_id FROM users WHERE name='Amit Kumar' LIMIT 1")

        if user1_id and user2_id:
            yesterday = datetime.now() - timedelta(days=1)
            two_days_ago = datetime.now() - timedelta(days=2)

            # Completed attendance — demo sample
            execute(
                """
                INSERT INTO attendance (user_id, entry_time, exit_time, status)
                VALUES (%s, %s, %s, 'Completed')
                """,
                (user1_id, yesterday.replace(hour=10, minute=0), yesterday.replace(hour=11, minute=30)),
            )
            execute(
                """
                INSERT INTO attendance (user_id, entry_time, exit_time, status)
                VALUES (%s, %s, %s, 'Completed')
                """,
                (user2_id, two_days_ago.replace(hour=14, minute=0), two_days_ago.replace(hour=15, minute=45)),
            )
        print("[seed] ✓ Attendance records seeded.")

    if _table_empty("sessions"):
        print("[seed] Inserting demo session records …")
        user1_id = fetch_scalar("SELECT user_id FROM users WHERE name='Rahul Sharma' LIMIT 1")
        user2_id = fetch_scalar("SELECT user_id FROM users WHERE name='Amit Kumar' LIMIT 1")

        if user1_id and user2_id:
            yesterday = datetime.now() - timedelta(days=1)
            two_days_ago = datetime.now() - timedelta(days=2)

            # Completed sessions — demo sample
            execute(
                """
                INSERT INTO sessions (user_id, lane_id, start_time, end_time, status)
                VALUES (%s, 'Lane 1', %s, %s, 'Completed')
                """,
                (user1_id, yesterday.replace(hour=10, minute=5), yesterday.replace(hour=11, minute=25)),
            )
            execute(
                """
                INSERT INTO sessions (user_id, lane_id, start_time, end_time, status)
                VALUES (%s, 'Lane 2', %s, %s, 'Completed')
                """,
                (user2_id, two_days_ago.replace(hour=14, minute=10), two_days_ago.replace(hour=15, minute=40)),
            )
        print("[seed] ✓ Sessions seeded.")

    if _table_empty("weapon_events"):
        print("[seed] Inserting demo weapon events …")
        user1_id = fetch_scalar("SELECT user_id FROM users WHERE name='Rahul Sharma' LIMIT 1")
        user2_id = fetch_scalar("SELECT user_id FROM users WHERE name='Amit Kumar' LIMIT 1")
        session1_id = fetch_scalar("SELECT session_id FROM sessions ORDER BY session_id LIMIT 1")
        session2_id = fetch_scalar(
            "SELECT session_id FROM sessions ORDER BY session_id LIMIT 1 OFFSET 1"
        )

        if user1_id and session1_id:
            yesterday = datetime.now() - timedelta(days=1)
            two_days_ago = datetime.now() - timedelta(days=2)

            # Demo weapon events — sample data
            execute(
                """
                INSERT INTO weapon_events
                  (session_id, user_id, weapon_type, confidence, detected_at, camera_id, lane_id)
                VALUES (%s, %s, 'Pistol', 0.92, %s, 'CAM-01', 'Lane 1')
                """,
                (session1_id, user1_id, yesterday.replace(hour=10, minute=15)),
            )
            execute(
                """
                INSERT INTO weapon_events
                  (session_id, user_id, weapon_type, confidence, detected_at, camera_id, lane_id)
                VALUES (%s, %s, 'Pistol', 0.88, %s, 'CAM-01', 'Lane 1')
                """,
                (session1_id, user1_id, yesterday.replace(hour=10, minute=45)),
            )

        if user2_id and session2_id:
            two_days_ago = datetime.now() - timedelta(days=2)
            execute(
                """
                INSERT INTO weapon_events
                  (session_id, user_id, weapon_type, confidence, detected_at, camera_id, lane_id)
                VALUES (%s, %s, 'Rifle', 0.79, %s, 'CAM-02', 'Lane 2')
                """,
                (session2_id, user2_id, two_days_ago.replace(hour=14, minute=20)),
            )
        print("[seed] ✓ Weapon events seeded.")

    print("[seed] Database seeding complete.")


if __name__ == "__main__":
    seed()

seed_all = seed

