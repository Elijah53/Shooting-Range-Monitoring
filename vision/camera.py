"""
vision/camera.py
----------------
Thin wrapper around cv2.VideoCapture.

macOS note
----------
On macOS 10.14+, the first call to cv2.VideoCapture() triggers a system
permission dialog.  The capture object may return isOpened()==False until
the user grants access and the process retries.  We handle this with a
short retry loop so the UI doesn't immediately throw a CameraError.

Usage
-----
    cam = Camera()
    cam.start()
    frame = cam.read_frame()   # returns an ndarray or None
    cam.stop()
"""

from __future__ import annotations

import os
import sys
import time

os.environ["OPENCV_AVFOUNDATION_SKIP_AUTH"] = "1"

import cv2
import numpy as np
from utils import config


class CameraError(Exception):
    """Raised when the camera cannot be opened or has been closed."""


class Camera:
    """Wraps cv2.VideoCapture with clean start/stop/read semantics."""

    # On macOS the permission prompt fires asynchronously; retry for up to
    # this many seconds before giving up.
    _MACOS_PERMISSION_RETRY_SECS = 3.0

    def __init__(self, source: str | int | None = None) -> None:
        raw = source if source is not None else config.CAMERA_SOURCE
        # Try to cast to int (webcam index); leave as str for RTSP/file paths.
        try:
            self._source: int | str = int(raw)
        except (ValueError, TypeError):
            self._source = str(raw)

        self._cap: cv2.VideoCapture | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """
        Open the camera.  Raises CameraError on failure.

        On macOS, retries for a short window to allow the system permission
        dialog to resolve.
        """
        is_macos = sys.platform == "darwin"
        deadline = time.monotonic() + (self._MACOS_PERMISSION_RETRY_SECS if is_macos else 0)

        while True:
            cap = cv2.VideoCapture(self._source)
            if cap.isOpened():
                self._cap = cap
                return

            cap.release()

            if time.monotonic() >= deadline:
                break
            time.sleep(0.3)

        # Final attempt failed — give a clear, actionable error message.
        if is_macos:
            raise CameraError(
                f"Could not open camera source '{self._source}'. "
                "On macOS, camera access must be granted to the terminal "
                "application running this app.\n\n"
                "👉 Go to: System Settings → Privacy & Security → Camera\n"
                "   and enable access for your terminal app "
                "(Terminal, iTerm2, VS Code, etc.), then restart the app."
            )
        raise CameraError(
            f"Could not open camera source '{self._source}'. "
            "Check that the camera is connected and not in use by another application."
        )

    def read_frame(self) -> np.ndarray | None:
        """
        Read one frame.  Returns an RGB ndarray or None if the read fails.
        Does NOT raise — callers should treat None as a transient failure.
        """
        if self._cap is None or not self._cap.isOpened():
            return None
        ret, frame = self._cap.read()
        if not ret or frame is None:
            return None
        # OpenCV returns BGR; convert to RGB for Streamlit / face_recognition.
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def read_frame_bgr(self) -> np.ndarray | None:
        """Read one frame in BGR format (for weapon detection with YOLO)."""
        if self._cap is None or not self._cap.isOpened():
            return None
        ret, frame = self._cap.read()
        if not ret or frame is None:
            return None
        return frame

    def stop(self) -> None:
        """Release the camera."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def __enter__(self) -> "Camera":
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()
