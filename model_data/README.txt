This folder is where the pretrained YOLO weapon-detection weights file
should go.

Expected filename (default): weapon_model.pt
Format: Ultralytics YOLO (v8-style) .pt checkpoint.

Standard YOLO/COCO weights do NOT include weapon classes, so you must
source a checkpoint that was already trained on a weapon dataset by
someone else (no training happens in this project). Community-trained
YOLOv8 weapon/pistol/rifle detection checkpoints are commonly shared on
platforms such as Hugging Face Hub or Roboflow Universe - search for
"yolov8 weapon detection weights" or "yolov8 pistol detection".

Steps:
1. Download a .pt file trained for weapon detection.
2. Place it in this folder (or anywhere you like).
3. Set WEAPON_MODEL_PATH in your .env to point at it, e.g.:
   WEAPON_MODEL_PATH=model_data/weapon_model.pt

If this file is not present, the app automatically runs in "mock mode":
weapon detection always reports nothing, and the Live Monitoring page
shows a banner explaining this. Everything else (face recognition,
attendance, sessions, dashboard, reports) still works normally in mock
mode, so you can demo/test the rest of the system first.
