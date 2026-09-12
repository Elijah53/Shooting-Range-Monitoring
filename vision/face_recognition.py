"""
vision/face_recognition.py
---------------------------
All face-recognition logic is isolated here so the underlying library can
be swapped without touching any other file.

Library: `face_recognition` (dlib-based, pretrained — no training required).

If the library is not installed, the module degrades gracefully:
- `FACE_RECOGNITION_AVAILABLE` is set to False.
- A human-readable install hint is stored in `INSTALL_HINT`.
- All public functions raise `FaceRecognitionUnavailableError` instead of
  crashing the whole application.
"""

from __future__ import annotations

import io
import pickle
import sys
from typing import Optional

import numpy as np

# ── Graceful import ────────────────────────────────────────────────────────────
# face_recognition's own __init__.py prints a "pip install" reminder to stdout
# at import time even when the package IS installed correctly.  We suppress that
# noise so it doesn't appear in Streamlit's output.
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



# ── Backward-compat aliases (used by pages/3_Users.py) ────────────────────────
FACE_LIB_AVAILABLE = FACE_RECOGNITION_AVAILABLE
IMPORT_ERROR = INSTALL_HINT  # human-readable install instructions if unavailable

# ── Custom exceptions ──────────────────────────────────────────────────────────

class FaceRecognitionUnavailableError(Exception):
    """Raised when the face_recognition library could not be imported."""


class NoFaceDetectedError(Exception):
    """Raised when no face is found in the supplied image."""


class MultipleFacesDetectedError(Exception):
    """Raised when more than one face is found during registration."""


# ── Encoding serialisation ─────────────────────────────────────────────────────

def serialize_encoding(encoding: np.ndarray) -> bytes:
    """Pickle a numpy encoding array for storage in a BYTEA column."""
    return pickle.dumps(encoding)


def deserialize_encoding(data: bytes) -> np.ndarray:
    """Unpickle a BYTEA value back to a numpy array."""
    return pickle.loads(data)


# ── Public API ─────────────────────────────────────────────────────────────────

def register_face(image: np.ndarray) -> np.ndarray:
    """
    Detect exactly one face in *image* (RGB ndarray) and return its
    128-dimensional encoding.

    Raises
    ------
    FaceRecognitionUnavailableError  — library not installed
    NoFaceDetectedError              — zero faces found
    MultipleFacesDetectedError       — more than one face found
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

    Parameters
    ----------
    frame           : RGB ndarray from the camera.
    known_encodings : {user_id: (name, encoding_array)}
    threshold       : Maximum face distance to count as a match (lower = stricter).

    Returns
    -------
    (user_id, name, confidence) where confidence is 1 - distance.
    Returns (None, None, 0.0) if no match or no face found.
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

    # Use the first (most prominent) face in the frame.
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
