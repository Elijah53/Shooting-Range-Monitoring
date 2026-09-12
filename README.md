# Shooting Range Attendance & Weapon Monitoring System

A beginner-friendly, computer-vision-based system for registered-user
identification, attendance, shooting-session tracking, and weapon
**type** observation (Pistol/Rifle/etc.), built for a controlled
shooting-range demo environment.

Uses only **pretrained** models — no custom ML training happens in this
project. Face recognition uses the `face_recognition` package; weapon
detection uses a configurable, externally-sourced pretrained YOLO model
(with an automatic mock-mode fallback if that model file is absent).

## What this system does NOT do

- It does **not** determine legal ownership of a weapon.
- It does **not** map a detected weapon type to a specific inventory
  item (e.g. it will say "Pistol", never "WPN-001").
- It does **not** do multi-person tracking — assume one active person
  in the camera's field of view at a time.

## 1. Prerequisites

- Python 3.10+
- PostgreSQL installed and running
- A webcam (or a phone screen showing a photo/video held up to the
  webcam, per the demo method below)

## 2. Setup

```bash
cd shooting_range_system
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Installing `face_recognition` / `dlib`

This is the step most likely to need extra setup, since `dlib` compiles
native code:

- **Windows**: install CMake (cmake.org) and "Visual Studio Build Tools"
  (Desktop development with C++ workload), then
  `pip install dlib` followed by `pip install face_recognition`.
  Alternative: `conda install -c conda-forge dlib`.
- **Linux**: `sudo apt-get install -y cmake build-essential`, then
  `pip install dlib face_recognition`.
- **macOS**: `brew install cmake`, then `pip install dlib face_recognition`.

If this library fails to install, the app still runs — face recognition
is simply skipped with a warning banner until it's fixed.

### Database

```sql
CREATE DATABASE shooting_range;
```

```bash
cp .env.example .env
# edit .env with your DB credentials
```

### Weapon detection model

No standard YOLO/COCO checkpoint contains weapon classes — you need to
source a pretrained weapon-detection `.pt` file yourself (see
`model_data/README.txt` for where these typically come from). Point
`WEAPON_MODEL_PATH` in `.env` at it. If you skip this step, the app runs
in **mock mode**: weapon detection always reports nothing, but everything
else (face recognition, attendance, sessions, dashboard, reports) works
normally, so you can build/test/demo the rest of the system first.

## 3. Run

```bash
streamlit run app.py
```

On first run the app will:
1. Check the database connection (shows setup instructions if it fails).
2. Create tables from `database/schema.sql` if they don't exist.
3. Insert demo/sample data (3 users, 3 weapons, 2 cameras, a little
   sample history) if the tables are empty.

## 4. Demo flow (no real weapon or range required)

1. Open **Live Monitoring**, pick a camera, click **Start Camera**.
2. Hold a phone up to the webcam displaying a registered user's photo.
   The system should recognize the face.
3. Hold up a phone photo/video of a weapon within the camera's view
   (requires a real weapon-detection model to be configured — otherwise
   you'll see the mock-mode banner and no weapon result).
4. When both a known face and a weapon are detected together, the app:
   creates/reuses an attendance record, creates/reuses a session, and
   logs a weapon event (throttled by a cooldown so repeated frames don't
   spam the database).
5. Open **Sessions** to manually **End Session**.
6. Check **Attendance**, **Weapon Events**, **Dashboard**, and **Reports**
   to see everything reflected from the database.

## 5. Project structure

```
shooting_range_system/
├── app.py                  # entry point, DB startup check
├── pages/                  # Streamlit multipage UI
├── vision/                 # camera, face recognition, weapon detection
├── services/               # business logic (users, attendance, sessions, events)
├── database/                # schema.sql, connection helpers, seed data
├── models/                  # plain dataclasses mirroring DB tables
├── utils/                   # config (.env) loading, small helpers
├── model_data/               # place your weapon_model.pt here
├── requirements.txt
└── .env.example
```

## 6. Testing checklist

- [ ] App starts; shows setup instructions if DB isn't configured yet.
- [ ] Register a user + capture a face in **Users**.
- [ ] Webcam opens in **Live Monitoring**; live frames render.
- [ ] Known face recognized; unknown face shows "Unknown" without
      creating attendance/session.
- [ ] Weapon detected shows type + confidence (or the mock-mode banner).
- [ ] Recognized user + detected weapon → attendance, session, and
      weapon event are all created.
- [ ] Recognized user + no weapon → no weapon event logged.
- [ ] Weapon detected + unrecognized user → nothing linked to any user.
- [ ] Repeated identical detections within the cooldown window don't
      create duplicate `weapon_events` rows.
- [ ] **End Session** in Sessions page sets `end_time` + `Completed`.
- [ ] Attendance / Weapon Events pages filter correctly by date.
- [ ] Dashboard metrics match the database.
- [ ] Reports CSV export downloads correctly.

## 7. Future enhancements (explicitly out of scope for this MVP)

RFID/barcode-based weapon-ownership verification, multi-person tracking,
anti-spoofing, ballistic/ammunition tracking, cloud deployment, mobile
app, distributed architecture.
# Shooting-Range-Monitoring
