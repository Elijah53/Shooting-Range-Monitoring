"""
vision/face_recognition.py
---------------------------
Biometric face encoding and recognition.

Biometric vectors (128-d floats) are saved and loaded as raw binary bytes
(IEEE 754 float64 array buffers) directly using NumPy into PostgreSQL's BYTEA
column, eliminating Python pickle dependencies and security risks.
"""

from __future__ import annotations

import io
import sys
from typing import Optional

import numpy as np

# ── Graceful import ────────────────────────────────────────────────────────────
try:
    import contextlib as _cl
    with _cl.redirect_stdout(io.StringIO()):
        import face_recognition as _fr

    FACE_RECOGNITION_AVAILABLE = True
    INSTALL_HINT = ""
except (ImportError, Exception, SystemExit):
    _fr = None  # type: ignore
    FACE_RECOGNITION_AVAILABLE = False

    _platform = sys.platform
    if _platform.startswith("win"):
        INSTALL_HINT = (
            "**face_recognition** is not installed.\n\n"
            "**Windows install steps:**\n"
            "1. Install [CMake](https://cmake.org/download/) and "
            "[Visual Studio Build Tools (C++)](https://visualstudio.microsoft.com/visual-cpp-build-tools/).\n"
            "2. Run: `pip install dlib`\n"
            "3. Run: `pip install face_recognition`\n\n"
            "Alternatively, with Conda: `conda install -c conda-forge dlib` then `pip install face_recognition`"
        )
    elif _platform == "darwin":
        INSTALL_HINT = (
            "**face_recognition** is not installed.\n\n"
            "**macOS install steps:**\n"
            "```\n"
            "brew install cmake\n"
            "pip install dlib face_recognition\n"
            "```"
        )
    else:
        INSTALL_HINT = (
            "**face_recognition** is not installed.\n\n"
            "**Linux install steps:**\n"
            "```\n"
            "sudo apt-get install -y cmake build-essential\n"
            "pip install dlib face_recognition\n"
            "```"
        )

FACE_LIB_AVAILABLE = FACE_RECOGNITION_AVAILABLE
IMPORT_ERROR = INSTALL_HINT


# ── Custom exceptions ──────────────────────────────────────────────────────────

class FaceRecognitionUnavailableError(Exception):
    """Raised when the face_recognition library could not be imported."""


class NoFaceDetectedError(Exception):
    """Raised when no face is found in the supplied image."""


class MultipleFacesDetectedError(Exception):
    """Raised when more than one face is found during registration."""


# ── Raw Binary Face Vector Serialization (NumPy) ──────────────────────────────

def serialize_encoding(encoding: np.ndarray) -> bytes:
    """
    Convert a 128-dimensional face encoding vector into raw binary bytes (float64).
    Stored directly into PostgreSQL BYTEA without pickle.
    """
    arr = np.asarray(encoding, dtype=np.float64)
    return arr.tobytes()


def deserialize_encoding(data: bytes | memoryview) -> np.ndarray:
    """
    Decode raw binary bytes directly into a 128-dimensional NumPy float64 array.
    Includes backward-compatible fallback for legacy pickled encodings.
    """
    if data is None:
        return np.empty((0,), dtype=np.float64)

    raw_bytes = bytes(data) if isinstance(data, memoryview) else data
    if len(raw_bytes) == 0:
        return np.empty((0,), dtype=np.float64)

    # 128 float64 = 1024 bytes; 128 float32 = 512 bytes
    if len(raw_bytes) == 1024:
        return np.frombuffer(raw_bytes, dtype=np.float64).copy()
    elif len(raw_bytes) == 512:
        return np.frombuffer(raw_bytes, dtype=np.float32).astype(np.float64).copy()

    # Legacy fallback for historical pickled records
    try:
        import pickle
        unpickled = pickle.loads(raw_bytes)
        return np.asarray(unpickled, dtype=np.float64)
    except Exception:
        return np.frombuffer(raw_bytes, dtype=np.float64).copy()


# ── Public API ─────────────────────────────────────────────────────────────────

def register_face(image: np.ndarray) -> np.ndarray:
    """
    Detect exactly one face in *image* (RGB ndarray) and return its
    128-dimensional encoding vector.
    """
    if not FACE_RECOGNITION_AVAILABLE:
        raise FaceRecognitionUnavailableError(INSTALL_HINT)

    locations = _fr.face_locations(image)
    if len(locations) == 0:
        raise NoFaceDetectedError("No face detected in the captured image.")
    if len(locations) > 1:
        raise MultipleFacesDetectedError(
            f"{len(locations)} faces detected. "
            "Please ensure only one person is in the frame during registration."
        )

    encodings = _fr.face_encodings(image, locations)
    return encodings[0]


def recognize_face(
    frame: np.ndarray,
    known_encodings: dict,          # {user_id: (name, np.ndarray)}
    threshold: float = 0.6,
) -> tuple[Optional[int], Optional[str], float]:
    """
    Compare all faces in *frame* against *known_encodings*.
    Returns (user_id, name, confidence).
    """
    if not FACE_RECOGNITION_AVAILABLE:
        raise FaceRecognitionUnavailableError(INSTALL_HINT)

    if not known_encodings:
        return None, None, 0.0

    locations = _fr.face_locations(frame)
    if not locations:
        return None, None, 0.0

    frame_encodings = _fr.face_encodings(frame, locations)
    if not frame_encodings:
        return None, None, 0.0

    frame_enc = frame_encodings[0]

    user_ids = list(known_encodings.keys())
    stored_encs = [known_encodings[uid][1] for uid in user_ids]
    names = [known_encodings[uid][0] for uid in user_ids]

    distances = _fr.face_distance(stored_encs, frame_enc)
    best_idx = int(np.argmin(distances))
    best_dist = float(distances[best_idx])

    if best_dist <= threshold:
        confidence = round(1.0 - best_dist, 4)
        return user_ids[best_idx], names[best_idx], confidence

    return None, None, 0.0
