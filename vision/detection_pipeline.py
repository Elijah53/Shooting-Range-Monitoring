"""
vision/detection_pipeline.py
----------------------------
Encapsulates computer vision inference (Face Recognition + Multi-Class YOLO Weapon Detection + Temporal Smoothing).

Responsibilities:
1. Receives raw camera RGB frames.
2. Fast face detection with downscaled HOG for responsive frame rates, followed by full-res encoding.
3. Multiple-face rejection and 128-d biometrics matching against registered shooters.
4. Pretrained multi-class YOLO threat detection & firearm classification.
5. Returns an annotated frame along with a pure DetectionResult dataclass.
NO database transactions are performed here.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Dict, Tuple, Optional, List
import cv2
import numpy as np

from models.detection_result import DetectionResult
from vision.face_recognition import FACE_RECOGNITION_AVAILABLE
from vision.weapon_detection import WeaponDetector, MockWeaponDetector, Detection, get_weapon_detector


class DetectionPipeline:
    """Coordinated vision pipeline with temporal stabilization and high-speed processing."""

    def __init__(
        self,
        weapon_detector: Optional[WeaponDetector | MockWeaponDetector] = None,
        face_match_threshold: float = 0.60,
        weapon_confidence_threshold: float = 0.45,
        face_interval: int = 4,
        weapon_interval: int = 1,
        buffer_size: int = 3,
    ) -> None:
        self.detector = weapon_detector or get_weapon_detector()
        self.face_threshold = face_match_threshold
        self.weapon_threshold = weapon_confidence_threshold
        self.face_interval = max(1, face_interval)
        self.weapon_interval = max(1, weapon_interval)

        # Pipeline counters & caches
        self.frame_counter: int = 0
        self._last_face_obs: Tuple[bool, bool, int, Optional[int], Optional[str], float, Optional[Tuple]] = (
            False, False, 0, None, None, 0.0, None
        )
        self._last_weapon_obs: Optional[Detection] = None

        # Temporal stabilization queues: stores recent candidate results
        self._face_history: deque = deque(maxlen=buffer_size)
        self._weapon_history: deque = deque(maxlen=buffer_size)

    def process_frame(
        self,
        frame_rgb: np.ndarray,
        face_encodings_cache: Dict[int, Tuple[str, np.ndarray]],
    ) -> Tuple[np.ndarray, DetectionResult]:
        """
        Execute detection pipeline on one RGB frame.

        Returns:
            (annotated_frame, DetectionResult)
        """
        self.frame_counter += 1
        fc = self.frame_counter
        h_f, w_f = frame_rgb.shape[:2]

        # ── 1. Fast Face Recognition Step (0.5x Downscale for Speed) ─────────
        if FACE_RECOGNITION_AVAILABLE and face_encodings_cache:
            if fc % self.face_interval == 1 or fc == 1:
                try:
                    import face_recognition
                    # 0.5x downscale makes HOG detection ~4x faster (~20ms)
                    small_frame = cv2.resize(frame_rgb, (0, 0), fx=0.5, fy=0.5)
                    face_locs_small = face_recognition.face_locations(small_frame, model="hog")
                    face_count = len(face_locs_small)

                    if face_count > 1:
                        # Multiple faces violation
                        self._last_face_obs = (True, True, face_count, None, None, 0.0, None)
                    elif face_count == 1:
                        # Exactly one face -> scale box back to original coordinates
                        top_s, right_s, bottom_s, left_s = face_locs_small[0]
                        orig_box = (top_s * 2, right_s * 2, bottom_s * 2, left_s * 2)
                        face_bbox = (left_s * 2, top_s * 2, right_s * 2, bottom_s * 2)

                        # Encode face at full resolution for biometric accuracy
                        frame_encs = face_recognition.face_encodings(frame_rgb, [orig_box])
                        if frame_encs:
                            frame_enc = frame_encs[0]
                            user_ids = list(face_encodings_cache.keys())
                            stored_encs = [face_encodings_cache[uid][1] for uid in user_ids]
                            names = [face_encodings_cache[uid][0] for uid in user_ids]

                            distances = face_recognition.face_distance(stored_encs, frame_enc)
                            best_idx = int(np.argmin(distances))
                            best_dist = float(distances[best_idx])

                            if best_dist <= self.face_threshold:
                                conf = round(1.0 - best_dist, 4)
                                self._last_face_obs = (
                                    True, False, 1, user_ids[best_idx], names[best_idx], conf, face_bbox
                                )
                            else:
                                self._last_face_obs = (
                                    True, False, 1, None, "Unregistered Person", 0.0, face_bbox
                                )
                        else:
                            self._last_face_obs = (True, False, 1, None, None, 0.0, face_bbox)
                    else:
                        # No face in view
                        self._last_face_obs = (False, False, 0, None, None, 0.0, None)
                except Exception:
                    self._last_face_obs = (False, False, 0, None, None, 0.0, None)
        else:
            self._last_face_obs = (False, False, 0, None, None, 0.0, None)

        # ── 2. Pretrained Multi-Class Weapon Detection Step ───────────────────
        if fc % self.weapon_interval == 0 or fc == 1:
            try:
                detections = self.detector.detect_weapon(frame_rgb)
                best_det = None
                for det in detections:
                    if det.confidence >= self.weapon_threshold:
                        if best_det is None or det.confidence > best_det.confidence:
                            best_det = det
                self._last_weapon_obs = best_det
            except Exception:
                self._last_weapon_obs = None

        # ── 3. Temporal Stabilization ─────────────────────────────────────────
        self._face_history.append(self._last_face_obs)
        self._weapon_history.append(self._last_weapon_obs)

        # Stabilize face result
        has_face, multi_face, f_count, uid, uname, f_conf, f_bbox = self._last_face_obs
        if len(self._face_history) >= 2:
            uid_votes = [obs[3] for obs in self._face_history if obs[3] is not None]
            if uid_votes:
                from collections import Counter
                most_common_uid, count = Counter(uid_votes).most_common(1)[0]
                if count >= 2:
                    matching_obs = next(obs for obs in reversed(self._face_history) if obs[3] == most_common_uid)
                    uid = matching_obs[3]
                    uname = matching_obs[4]
                    f_conf = matching_obs[5]
                    f_bbox = matching_obs[6]
                    has_face = True
                    multi_face = False
                else:
                    uid, uname, f_conf = None, None, 0.0

        # Stabilize weapon result (requires at least 2 consistent frames out of buffer)
        weapon_detected = False
        wpn_type, wpn_cat, wpn_conf, wpn_bbox, wpn_details = None, None, 0.0, None, None
        valid_weapons = [w for w in self._weapon_history if w is not None]
        if len(valid_weapons) >= 2:
            best_recent = max(valid_weapons, key=lambda d: d.confidence)
            weapon_detected = True
            wpn_type = best_recent.weapon_type
            wpn_cat = getattr(best_recent, "category", "Firearm")
            wpn_conf = best_recent.confidence
            wpn_bbox = best_recent.bbox
            wpn_details = getattr(best_recent, "details", "")

        # ── 4. Build Pure DetectionResult ─────────────────────────────────────
        result = DetectionResult(
            face_detected=has_face,
            multiple_faces=multi_face,
            face_count=f_count,
            user_id=uid,
            user_name=uname,
            face_confidence=f_conf,
            face_bbox=f_bbox,
            weapon_detected=weapon_detected,
            weapon_type=wpn_type,
            weapon_category=wpn_cat,
            weapon_confidence=wpn_conf,
            weapon_bbox=wpn_bbox,
            weapon_details=wpn_details,
            frame_number=fc,
            timestamp=time.time(),
        )

        # ── 5. Annotate Frame ─────────────────────────────────────────────────
        annotated = frame_rgb.copy()

        # Draw Face Bounding Box
        if f_bbox and not multi_face:
            x1, y1, x2, y2 = f_bbox
            color = (0, 220, 100) if uid is not None else (0, 180, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            face_lbl = f"{uname} ({f_conf:.0%})" if uname else "Face Detected"
            cv2.putText(
                annotated, face_lbl, (x1, max(18, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
            )

        # Draw Weapon Bounding Box
        if wpn_bbox:
            wx1, wy1, wx2, wy2 = wpn_bbox
            w_color = (0, 70, 255)
            cv2.rectangle(annotated, (wx1, wy1), (wx2, wy2), w_color, 3)
            w_label = f"{wpn_type} [{wpn_conf:.0%}]"
            cv2.rectangle(annotated, (wx1, max(0, wy1 - 28)), (wx1 + len(w_label) * 12 + 6, wy1), w_color, -1)
            cv2.putText(
                annotated, w_label, (wx1 + 4, max(16, wy1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2
            )

        # Draw Multiple Faces Alert Banner
        if multi_face:
            cv2.rectangle(annotated, (10, 10), (w_f - 10, 60), (0, 0, 220), -1)
            cv2.putText(
                annotated,
                f"MULTIPLE PEOPLE DETECTED ({f_count}) — ONLY 1 ALLOWED",
                (20, 44),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )

        return annotated, result
