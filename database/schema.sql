-- database/schema.sql
-- All tables use CREATE TABLE IF NOT EXISTS so init_db() is idempotent.

CREATE TABLE IF NOT EXISTS users (
    user_id           SERIAL PRIMARY KEY,
    name              VARCHAR(100) NOT NULL,
    phone             VARCHAR(20),
    face_encoding     BYTEA,                         -- pickled numpy array
    registration_date TIMESTAMP DEFAULT NOW(),
    status            VARCHAR(20) DEFAULT 'Active'
                        CHECK (status IN ('Active', 'Inactive'))
);

CREATE TABLE IF NOT EXISTS weapons (
    weapon_id   VARCHAR(20) PRIMARY KEY,             -- e.g. WPN-001
    weapon_type VARCHAR(50) NOT NULL,                -- e.g. Pistol, Rifle
    status      VARCHAR(20) DEFAULT 'Available'
                  CHECK (status IN ('Available', 'In Use', 'Maintenance'))
);

CREATE TABLE IF NOT EXISTS cameras (
    camera_id VARCHAR(20) PRIMARY KEY,               -- e.g. CAM-01
    lane_id   VARCHAR(20) NOT NULL,                  -- e.g. Lane 1
    status    VARCHAR(20) DEFAULT 'Online'
                CHECK (status IN ('Online', 'Offline'))
);

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(user_id),
    entry_time    TIMESTAMP DEFAULT NOW(),
    exit_time     TIMESTAMP,
    status        VARCHAR(20) DEFAULT 'Active'
                    CHECK (status IN ('Active', 'Completed'))
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(user_id),
    lane_id    VARCHAR(20) NOT NULL,
    start_time TIMESTAMP DEFAULT NOW(),
    end_time   TIMESTAMP,
    status     VARCHAR(20) DEFAULT 'Active'
                 CHECK (status IN ('Active', 'Completed'))
);

CREATE TABLE IF NOT EXISTS weapon_events (
    event_id    SERIAL PRIMARY KEY,
    session_id  INTEGER REFERENCES sessions(session_id),
    user_id     INTEGER REFERENCES users(user_id),
    weapon_type VARCHAR(50) NOT NULL,
    confidence  NUMERIC(5, 2) NOT NULL,
    detected_at TIMESTAMP DEFAULT NOW(),
    camera_id   VARCHAR(20) REFERENCES cameras(camera_id),
    lane_id     VARCHAR(20),
    manual_weapon_type   VARCHAR(50),
    manually_verified_by VARCHAR(100),
    manually_verified_at TIMESTAMP
);

-- Additive migration for existing installations
ALTER TABLE weapon_events
    ADD COLUMN IF NOT EXISTS manual_weapon_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS manually_verified_by VARCHAR(100),
    ADD COLUMN IF NOT EXISTS manually_verified_at TIMESTAMP;

-- App settings: single-row table for runtime-configurable values.
-- Editable via the Settings page; loaded at startup.
CREATE TABLE IF NOT EXISTS app_settings (
    id                              INTEGER PRIMARY KEY DEFAULT 1,
    face_match_threshold            NUMERIC(4, 2) DEFAULT 0.6,
    detection_confidence_threshold  NUMERIC(4, 2) DEFAULT 0.5,
    event_cooldown_seconds          INTEGER DEFAULT 7,
    face_recognition_interval       INTEGER DEFAULT 10,
    camera_source                   VARCHAR(100) DEFAULT '0',
    CONSTRAINT single_row CHECK (id = 1)
);

-- Insert the default settings row if absent.
INSERT INTO app_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_attendance_user        ON attendance(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user          ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_weapon_events_session  ON weapon_events(session_id);
CREATE INDEX IF NOT EXISTS idx_weapon_events_detected ON weapon_events(detected_at);
