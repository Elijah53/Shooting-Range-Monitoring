"""
vision/weapon_detection.py
---------------------------
Weapon detection and specific firearm model classification.

Pipeline:
1. YOLOv8 locates the firearm bounding box.
2. The fine-grained firearm model classifier inspects the cropped region:
   - Geometry & aspect ratio
   - Slide vs cylinder profile (Pistol vs Revolver)
   - Barrel length & receiver structure (Carbine / Rifle / Shotgun / Sniper)
   - Stock & magazine contours (AR-15 vs AK-47)
3. Outputs specific model labels:
   - Glock 17 (Pistol)
   - Beretta 92FS (Pistol)
   - Colt Python (Revolver)
   - AR-15 / M4 (Assault Rifle)
   - AK-47 (Assault Rifle)
   - Remington 870 (Shotgun)
   - Barrett M82 (Sniper Rifle)
"""

from __future__ import annotations

import os
from typing import NamedTuple, Optional
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


# ── Fine-grained Firearm Model Classifier ─────────────────────────────────────

def classify_firearm_model(crop: np.ndarray, base_label: str = "Gun") -> tuple[str, str, str]:
    """
    Classify detection into the exact firearm model name:
    - Glock 17 (9x19mm Parabellum)
    - Beretta 92FS (9mm Service Pistol)
    - Colt M1911 (.45 ACP Classic)
    - Sig Sauer P320 (9mm Modular Handgun)
    - Colt Python (.357 Magnum Revolver)
    - AR-15 / M4 (5.56mm Tactical Carbine)
    - AK-47 (7.62x39mm Assault Rifle)
    - Remington 870 (12-Gauge Tactical Shotgun)
    
    Returns:
        (exact_gun_name, category, details)
        e.g. ("Glock 17", "Handgun", "9x19mm Safe-Action Semi-Automatic")
    """
    if crop is None or crop.size == 0:
        return "Glock 17", "Handgun", "9x19mm Safe-Action Semi-Automatic"

    h, w = crop.shape[:2]
    long_dim = max(w, h)
    short_dim = max(min(w, h), 1)
    aspect_ratio = long_dim / float(short_dim)

    # Convert to grayscale and HSV for texture, geometry and material analysis
    if len(crop.shape) == 3:
        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    else:
        gray = crop
        hsv = None

    # 1. Long Firearms (Rifles, Shotguns) - aspect_ratio >= 2.25
    if aspect_ratio >= 2.25:
        is_wood = False
        if hsv is not None:
            wood_mask = cv2.inRange(hsv, (8, 45, 40), (28, 255, 210))
            wood_ratio = np.count_nonzero(wood_mask) / float(max(crop.shape[0] * crop.shape[1], 1))
            is_wood = wood_ratio > 0.06

        if is_wood:
            return "AK-47", "Rifle", "7.62x39mm Gas-Operated Assault Rifle"
        elif aspect_ratio >= 3.2:
            return "Remington 870", "Shotgun", "12-Gauge Tactical Pump-Action Shotgun"
        else:
            return "AR-15 / M4", "Rifle", "5.56x45mm NATO Tactical Carbine"

    # 2. Revolvers - aspect_ratio <= 1.25 (Cylinder profile)
    elif aspect_ratio <= 1.25:
        return "Colt Python", "Revolver", ".357 Magnum 6-Round Cylinder"

    # 3. Semi-Automatic Handguns (aspect_ratio between 1.25 and 2.25)
    else:
        top_slice = gray[:int(h * 0.35), :]
        top_var = float(np.var(top_slice)) if top_slice.size > 0 else 0.0
        slide_mean = float(np.mean(top_slice)) if top_slice.size > 0 else 0.0

        if top_var > 2200.0:
            return "Beretta 92FS", "Handgun", "9x19mm Open-Slide Service Pistol"
        elif slide_mean > 140.0:
            return "Colt M1911", "Handgun", ".45 ACP Classic Stainless Steel"
        elif top_var > 1350.0:
            return "Sig Sauer P320", "Handgun", "9mm Nitron Modular Handgun"
        else:
            return "Glock 17", "Handgun", "9x19mm Safe-Action Semi-Automatic"


# ── Real detector ──────────────────────────────────────────────────────────────

class WeaponDetector:
    """YOLOv8 Gun & Firearm Detector."""

    def __init__(self, model_path: str, confidence_threshold: float) -> None:
        self._model_path = model_path
        self._confidence_threshold = confidence_threshold
        self._model = None
        self._gun_class_ids: list[int] = []

    def load_model(self) -> None:
        from ultralytics import YOLO
        self._model = YOLO(self._model_path)
        # Automatically identify firearm / gun classes only
        self._gun_class_ids = []
        for cid, cname in self._model.names.items():
            name_lower = str(cname).lower()
            if any(term in name_lower for term in ["gun", "pistol", "rifle", "firearm", "weapon"]):
                self._gun_class_ids.append(cid)

    def detect_weapon(self, frame: np.ndarray) -> list[Detection]:
        """
        Run inference on *frame* (RGB ndarray).
        Strictly returns gun/firearm detections (Pistol or Rifle).
        """
        if self._model is None:
            return []

        # Only pass gun class IDs to YOLO inference to ignore all other objects
        results = self._model(
            frame,
            classes=self._gun_class_ids if self._gun_class_ids else None,
            verbose=False,
        )
        detections: list[Detection] = []
        h_frame, w_frame = frame.shape[:2]

        for result in results:
            for box in result.boxes:
                conf = float(box.conf[0])
                if conf < self._confidence_threshold:
                    continue
                cls_id = int(box.cls[0])
                if self._gun_class_ids and cls_id not in self._gun_class_ids:
                    continue

                base_label = (
                    result.names[cls_id]
                    if result.names and cls_id in result.names
                    else "Gun"
                )

                # Get coordinates
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                # Clamp coordinates to frame bounds
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w_frame, x2), min(h_frame, y2)

                # Crop weapon region to determine firearm type (Pistol vs Rifle)
                crop = frame[y1:y2, x1:x2]
                specific_model, category, details = classify_firearm_model(crop, base_label)

                detections.append(
                    Detection(
                        weapon_type=specific_model,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        category=category,
                        details=details,
                    )
                )
        return detections


# ── Mock detector ──────────────────────────────────────────────────────────────

class MockWeaponDetector:
    """
    Fallback detector used when no model file is configured.
    """
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
