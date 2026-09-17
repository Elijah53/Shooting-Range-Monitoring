"""
vision/camera.py
----------------
High-performance threaded video capture driver.

Features:
1. Dedicated background reader thread continuously drains the camera hardware
   buffer, eliminating queue buildup, lag, and frame drops.
2. Direct O(1) non-blocking access to the most recent frame.
3. Locks target frame rate and hardware auto-exposure settings to avoid
   lighting flicker during computer vision inference.
"""

from __future__ import annotations

import os
import sys
import time
import threading
from typing import Optional

os.environ["OPENCV_AVFOUNDATION_SKIP_AUTH"] = "1"

import cv2
import numpy as np
from utils import config


class CameraError(Exception):
    """Raised when the camera cannot be opened or has been closed."""


class Camera:
    """Threaded camera capture driver with zero buffer latency."""

    _MACOS_PERMISSION_RETRY_SECS = 3.0

    def __init__(self, source: str | int | None = None, target_fps: int = 30) -> None:
        raw = source if source is not None else config.CAMERA_SOURCE
        try:
            self._source: int | str = int(raw)
        except (ValueError, TypeError):
            self._source = str(raw)

        self._target_fps = target_fps
        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._lock: threading.Lock = threading.Lock()

        self._latest_frame_rgb: Optional[np.ndarray] = None
        self._latest_frame_bgr: Optional[np.ndarray] = None
        self._last_frame_timestamp: float = 0.0

    def start(self) -> None:
        """
        Open camera device and start background frame reader thread.
        """
        if self._running and self._cap is not None and self._cap.isOpened():
            return

        is_macos = sys.platform == "darwin"
        deadline = time.monotonic() + (self._MACOS_PERMISSION_RETRY_SECS if is_macos else 0)

        cap = None
        while True:
            # Use CAP_AVFOUNDATION on macOS or standard backend
            if is_macos and isinstance(self._source, int):
                cap = cv2.VideoCapture(self._source, cv2.CAP_AVFOUNDATION)
            else:
                cap = cv2.VideoCapture(self._source)

            if cap.isOpened():
                break

            cap.release()
            if time.monotonic() >= deadline:
                break
            time.sleep(0.3)

        if cap is None or not cap.isOpened():
            if is_macos:
                raise CameraError(
                    f"Could not open camera source '{self._source}'. "
                    "On macOS, camera access must be granted to the terminal "
                    "application running this app.\n\n"
                    "👉 Go to: System Settings → Privacy & Security → Camera\n"
                    "   and enable access for your terminal app, then restart."
                )
            raise CameraError(
                f"Could not open camera source '{self._source}'. "
                "Check that the camera is connected and not in use by another application."
            )

        # ── Driver Hardware Optimizations & Locking ───────────────────────────
        # 1. Minimize driver buffer latency to 1 frame to prevent buffer lag
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        # 2. Lock target frame rate
        try:
            cap.set(cv2.CAP_PROP_FPS, float(self._target_fps))
        except Exception:
            pass

        # 3. Lock camera exposure to prevent lighting shifts & brightness hunting
        try:
            # For V4L2/AVFoundation: 0.25 / 0 / 1 are common manual/fixed modes
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        except Exception:
            pass

        self._cap = cap
        self._running = True

        # Grab first frame synchronously
        ret, initial_frame = cap.read()
        if ret and initial_frame is not None:
            self._latest_frame_bgr = initial_frame
            self._latest_frame_rgb = cv2.cvtColor(initial_frame, cv2.COLOR_BGR2RGB)
            self._last_frame_timestamp = time.time()

        # Start dedicated background reader thread
        self._thread = threading.Thread(
            target=self._capture_worker,
            name="CameraCaptureWorker",
            daemon=True,
        )
        self._thread.start()

    def _capture_worker(self) -> None:
        """Background loop continuously draining the hardware buffer."""
        target_interval = 1.0 / max(1, self._target_fps)

        while self._running and self._cap is not None and self._cap.isOpened():
            loop_start = time.monotonic()
            ret, frame = self._cap.read()
            if ret and frame is not None:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                with self._lock:
                    self._latest_frame_bgr = frame
                    self._latest_frame_rgb = rgb_frame
                    self._last_frame_timestamp = time.time()
            else:
                time.sleep(0.01)

            elapsed = time.monotonic() - loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0.002:
                time.sleep(sleep_time)

    def read_frame(self) -> Optional[np.ndarray]:
        """
        Return the most recently captured RGB frame without blocking on I/O.
        Returns None if no frame is available yet or camera is closed.
        """
        with self._lock:
            if self._latest_frame_rgb is None:
                return None
            return self._latest_frame_rgb.copy()

    def read_frame_bgr(self) -> Optional[np.ndarray]:
        """
        Return the most recently captured BGR frame without blocking on I/O.
        """
        with self._lock:
            if self._latest_frame_bgr is None:
                return None
            return self._latest_frame_bgr.copy()

    def stop(self) -> None:
        """Stop background capture and release hardware resources."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

        if self._cap is not None:
            self._cap.release()
            self._cap = None

        with self._lock:
            self._latest_frame_rgb = None
            self._latest_frame_bgr = None

    @property
    def is_open(self) -> bool:
        return self._running and self._cap is not None and self._cap.isOpened()

    def __enter__(self) -> "Camera":
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()
