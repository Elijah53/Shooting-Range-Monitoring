"""
vision/weapon_detection.py
---------------------------
Pretrained multi-class YOLO weapon detection.

Supports multi-class checkpoints (e.g. Rifle vs Pistol vs Heavy Weapon vs Knife)
and maps model outputs directly to firearm categories.
"""

from __future__ import annotations

import os
from typing import NamedTuple, Optional, List
import cv2
import numpy as np

from utils import config


# ── Detection result type ──────────────────────────────────────────────────────

class Detection(NamedTuple):
    weapon_type: str
    confidence: float
    bbox: tuple[int, int, int, int]   # x1, y1, x2, y2
    category: str = "Firearm"
    details: str = ""


# ── Standard Weapon Name Normalization ─────────────────────────────────────────

STANDARD_WEAPON_MAP = {
    "rifle": ("Rifle", "Firearm", "Tactical / Long Barrel Rifle"),
    "assault_rifle": ("Rifle", "Firearm", "Tactical Assault Rifle"),
    "heavy_weapon": ("Rifle", "Firearm", "Tactical Long Firearm"),
    "shotgun": ("Shotgun", "Firearm", "Pump-Action / Tactical Shotgun"),
    "pistol": ("Pistol", "Firearm", "Handgun / Sidearm"),
    "handgun": ("Pistol", "Firearm", "Handgun / Sidearm"),
    "revolver": ("Revolver", "Firearm", "Revolver Cylinder Handgun"),
    "gun": ("Pistol", "Firearm", "Firearm / Handgun"),
}

NON_WEAPON_CLASSES = {"person", "human", "face", "background", "hand", "cell_phone", "phone", "knife", "blade", "grenade", "explosion"}


def normalize_weapon_label(class_name: str, class_id: int, bbox: tuple[int, int, int, int]) -> tuple[Optional[str], str, str]:
    """
    Map the predicted class label/index directly from the YOLO model output.
    Returns (None, '', '') if the detected class is non-firearm or unrecognized noise.
    """
    name_clean = str(class_name).strip().lower().replace("-", "_").replace(" ", "_")

    # Reject non-firearm classes explicitly
    if name_clean in NON_WEAPON_CLASSES:
        return None, "", ""

    # 1. Direct match for explicit firearm classes
    for key, (w_type, cat, desc) in STANDARD_WEAPON_MAP.items():
        if key in name_clean:
            # If explicit rifle or shotgun or revolver, return immediately
            if key in ("rifle", "assault_rifle", "heavy_weapon", "shotgun", "revolver"):
                return w_type, cat, desc

    # 2. Generic weapon/gun terms -> check geometry
    if any(term in name_clean for term in ("gun", "weapon", "firearm", "pistol", "handgun")):
        x1, y1, x2, y2 = bbox
        box_w = max(1, x2 - x1)
        box_h = max(1, y2 - y1)
        aspect_ratio = max(box_w, box_h) / float(min(box_w, box_h))

        # Long firearms (rifles, carbines, shotguns) have aspect ratio >= 2.0
        if aspect_ratio >= 2.0:
            return "Rifle", "Firearm", "Tactical Rifle / Long Gun"
        return "Pistol", "Firearm", "Handgun / Sidearm"

    # If it has no firearm-related keyword, do not treat as a weapon
    return None, "", ""


# ── Real detector ──────────────────────────────────────────────────────────────

class WeaponDetector:
    """Pretrained YOLO Firearm Weapon Detector."""

    def __init__(self, model_path: str, confidence_threshold: float) -> None:
        self._model_path = model_path
        self._confidence_threshold = confidence_threshold
        self._model = None
        self._weapon_class_ids: list[int] = []

    def load_model(self) -> None:
        from ultralytics import YOLO
        self._model = YOLO(self._model_path)
        
        # Identify firearm-related class IDs from model metadata if present
        self._weapon_class_ids = []
        if hasattr(self._model, "names") and self._model.names:
            for cid, cname in self._model.names.items():
                name_lower = str(cname).lower()
                if any(term in name_lower for term in ["gun", "pistol", "rifle", "shotgun", "firearm", "weapon", "handgun", "heavy"]):
                    if not any(nw in name_lower for nw in ["person", "human", "face", "knife", "blade", "grenade"]):
                        self._weapon_class_ids.append(cid)

    def detect_weapon(self, frame: np.ndarray) -> list[Detection]:
        """
        Run inference on *frame* (RGB ndarray).
        Directly extracts weapon category and confidence from YOLO model predictions.
        """
        if self._model is None:
            return []

        h_frame, w_frame = frame.shape[:2]
        min_dim = min(h_frame, w_frame)
        min_box_size = max(28, int(min_dim * 0.05))  # Minimum dimension to discard tiny false-positive noise
        min_area = int(0.003 * h_frame * w_frame)    # Minimum 0.3% of screen area

        results = self._model(
            frame,
            conf=max(0.20, self._confidence_threshold),
            iou=0.45,
            classes=self._weapon_class_ids if self._weapon_class_ids else None,
            verbose=False,
        )
        detections: list[Detection] = []

        for result in results:
            if not result.boxes:
                continue
            for box in result.boxes:
                conf = float(box.conf[0])
                if conf < self._confidence_threshold:
                    continue
                cls_id = int(box.cls[0])
                if self._weapon_class_ids and cls_id not in self._weapon_class_ids:
                    continue

                raw_label = (
                    result.names[cls_id]
                    if result.names and cls_id in result.names
                    else f"Class_{cls_id}"
                )

                # Bounding box coordinates clamped to frame
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w_frame, x2), min(h_frame, y2)
                bw, bh = x2 - x1, y2 - y1

                # Discard noise detections with unrealistic dimensions
                if bw < min_box_size and bh < min_box_size:
                    continue
                if (bw * bh) < min_area:
                    continue

                # Map to standardized firearm name and category
                weapon_type, category, details = normalize_weapon_label(raw_label, cls_id, (x1, y1, x2, y2))
                if weapon_type is None:
                    continue

                detections.append(
                    Detection(
                        weapon_type=weapon_type,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        category=category,
                        details=details,
                    )
                )
        return detections


# ── Mock detector ──────────────────────────────────────────────────────────────

class MockWeaponDetector:
    """Fallback detector used when no model file is configured."""
    MOCK_MODE = True

    def load_model(self) -> None:
        pass

    def detect_weapon(self, frame: np.ndarray) -> list[Detection]:
        return []


# ── Factory ────────────────────────────────────────────────────────────────────

def get_weapon_detector(
    model_path: str | None = None,
    confidence_threshold: float | None = None,
) -> WeaponDetector | MockWeaponDetector:
    """
    Return a WeaponDetector if the model file exists, otherwise a
    MockWeaponDetector. Calls load_model() before returning.
    """
    path = model_path or config.WEAPON_MODEL_PATH
    # Default to multi_weapon_model.pt if exists
    if not os.path.isfile(path) and os.path.isfile("model_data/multi_weapon_model.pt"):
        path = "model_data/multi_weapon_model.pt"

    threshold = (
        confidence_threshold
        if confidence_threshold is not None
        else config.DETECTION_CONFIDENCE_THRESHOLD
    )

    if os.path.isfile(path):
        detector: WeaponDetector | MockWeaponDetector = WeaponDetector(path, threshold)
    else:
        detector = MockWeaponDetector()

    detector.load_model()
    return detector
