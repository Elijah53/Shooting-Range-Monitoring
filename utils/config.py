"""
utils/config.py
---------------
Central configuration loader.  All other modules import from here —
never read os.environ or .env directly elsewhere.
"""

import os
import pathlib
from dotenv import load_dotenv

# Load .env from the project root using an absolute path so this works
# regardless of the current working directory (e.g. when Streamlit pages
# are run as independent scripts).
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _get(key: str, default=None, cast=None):
    """Read an env var, apply an optional cast, and fall back to default."""
    value = os.environ.get(key, default)
    if value is None:
        return default
    if cast is not None:
        try:
            return cast(value)
        except (ValueError, TypeError):
            return default
    return value


# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL: str | None = _get("DATABASE_URL")
DB_HOST: str = _get("DB_HOST", "localhost")
DB_PORT: int = _get("DB_PORT", 5432, int)
DB_NAME: str = _get("DB_NAME", "shooting_range")
DB_USER: str = _get("DB_USER", "postgres")
DB_PASSWORD: str = _get("DB_PASSWORD", "")

# ── Vision ────────────────────────────────────────────────────────────────────
WEAPON_MODEL_PATH: str = _get("WEAPON_MODEL_PATH", "model_data/weapon_model.pt")
CAMERA_SOURCE: str = _get("CAMERA_SOURCE", "0")  # kept as str; cast to int in camera.py

# ── Thresholds & Timing ───────────────────────────────────────────────────────
FACE_MATCH_THRESHOLD: float = _get("FACE_MATCH_THRESHOLD", 0.6, float)
DETECTION_CONFIDENCE_THRESHOLD: float = _get("DETECTION_CONFIDENCE_THRESHOLD", 0.5, float)
EVENT_COOLDOWN_SECONDS: int = _get("EVENT_COOLDOWN_SECONDS", 7, int)
FACE_RECOGNITION_INTERVAL: int = _get("FACE_RECOGNITION_INTERVAL", 10, int)


# ── Compatibility helper ───────────────────────────────────────────────────────
class _Settings:
    """Simple namespace returned by load_settings() for backward compat."""
    def __init__(self):
        self.camera_source = CAMERA_SOURCE
        self.face_match_threshold = FACE_MATCH_THRESHOLD
        self.detection_confidence_threshold = DETECTION_CONFIDENCE_THRESHOLD
        self.event_cooldown_seconds = EVENT_COOLDOWN_SECONDS
        self.face_recognition_interval = FACE_RECOGNITION_INTERVAL
        self.weapon_model_path = WEAPON_MODEL_PATH

def load_settings() -> _Settings:
    """Return a settings namespace (reads from DB if available, else .env)."""
    try:
        from database.database import fetch_one
        row = fetch_one("SELECT * FROM app_settings WHERE id = 1")
        s = _Settings()
        if row:
            s.detection_confidence_threshold = float(row.get("detection_confidence_threshold") or s.detection_confidence_threshold)
            s.event_cooldown_seconds = int(row.get("event_cooldown_seconds") or s.event_cooldown_seconds)
            s.face_recognition_interval = int(row.get("face_recognition_interval") or s.face_recognition_interval)
            s.camera_source = str(row.get("camera_source") or s.camera_source)
        return s
    except Exception:
        return _Settings()
