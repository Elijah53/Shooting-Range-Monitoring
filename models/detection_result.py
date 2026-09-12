"""
models/detection_result.py
--------------------------
Data model representing the outcome of a single video frame inspection
produced by the DetectionPipeline.

Contains pure vision observations (face recognition + weapon detection)
with NO database transactions or business side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class DetectionResult:
    """Pure computer vision detection output for one frame."""

    # ── Face Recognition Observations ─────────────────────────────────────────
    face_detected: bool = False
    multiple_faces: bool = False
    face_count: int = 0
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    face_confidence: float = 0.0
    face_bbox: Optional[Tuple[int, int, int, int]] = None   # (x1, y1, x2, y2)

    # ── Weapon Detection Observations ─────────────────────────────────────────
    weapon_detected: bool = False
    weapon_type: Optional[str] = None                       # Specific model (e.g. "Glock 17 (Pistol)")
    weapon_category: Optional[str] = None                   # Category (e.g. "Pistol", "Rifle", "Revolver")
    weapon_confidence: float = 0.0
    weapon_bbox: Optional[Tuple[int, int, int, int]] = None # (x1, y1, x2, y2)
    weapon_details: Optional[str] = None                    # Caliber & specs description

    # ── Pipeline Metadata ─────────────────────────────────────────────────────
    frame_number: int = 0
    timestamp: float = 0.0
