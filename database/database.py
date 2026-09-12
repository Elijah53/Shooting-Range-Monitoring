"""
database/database.py
--------------------
All DB connectivity for the application.

Performance note
----------------
A ConnectionPool is created once per Streamlit server process and cached
via @st.cache_resource. If psycopg_pool is not installed, a resilient
connection manager fallback is provided so the application never crashes.

Public API
----------
DatabaseUnavailableError  → Exception
check_connection()        → bool
require_db_or_stop()      → None (shows UI error and halts page if DB is down)
get_connection()          → psycopg.Connection (context-managed borrow)
init_db()                 → None (runs schema.sql, idempotent)
execute(sql, params)      → None
fetch_one(sql, params)    → dict | None
fetch_all(sql, params)    → list[dict]
fetch_scalar(sql, params) → Any
"""

from __future__ import annotations

import pathlib
from contextlib import contextmanager
from typing import Any, Optional, Generator

import psycopg
import streamlit as st
from psycopg.rows import dict_row

try:
    from psycopg_pool import ConnectionPool
except (ImportError, ModuleNotFoundError):
    ConnectionPool = None

from utils import config

# Path to the SQL schema file, relative to this file.
_SCHEMA_FILE = pathlib.Path(__file__).parent / "schema.sql"


class DatabaseUnavailableError(Exception):
    """Raised when the database cannot be reached."""


# ── DSN builder ───────────────────────────────────────────────────────────────

def _build_dsn() -> str:
    """Build a libpq connection string from config."""
    if config.DATABASE_URL:
        return config.DATABASE_URL
    parts = [
        f"host={config.DB_HOST}",
        f"port={config.DB_PORT}",
        f"dbname={config.DB_NAME}",
        f"user={config.DB_USER}",
    ]
    if config.DB_PASSWORD:
        parts.append(f"password={config.DB_PASSWORD}")
    return " ".join(parts)


# ── Connection Management & Pooling ──────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_pool():
    """
    Create and return a single shared ConnectionPool if psycopg_pool is available,
    or None to signal fallback to direct managed connections.
    """
    if ConnectionPool is None:
        return None

    dsn = _build_dsn()
    try:
        pool = ConnectionPool(
            conninfo=dsn,
            min_size=2,
            max_size=10,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        return pool
    except Exception:
        # Fall back gracefully if pool cannot open immediately
        return None


@contextmanager
def get_connection() -> Generator[psycopg.Connection, None, None]:
    """
    Borrow a connection from the pool if available, or create a direct connection.
    Guarantees auto-closure / return on context manager exit.
    """
    pool = get_pool()
    if pool is not None:
        with pool.connection() as conn:
            yield conn
    else:
        dsn = _build_dsn()
        try:
            conn = psycopg.connect(dsn, row_factory=dict_row)
        except Exception as e:
            raise DatabaseUnavailableError(f"Cannot connect to database: {e}") from e
        try:
            yield conn
        finally:
            conn.close()


# ── Diagnostics & Safety Checks ───────────────────────────────────────────────

def check_db_connection() -> tuple[bool, str]:
    """Test if database is reachable."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True, "Connected"
    except Exception as e:
        return False, str(e)


def check_connection() -> bool:
    """Return True if PostgreSQL is reachable, False otherwise."""
    ok, _ = check_db_connection()
    return ok


def require_db_or_stop() -> None:
    """Check database connection and show error & stop page if unreachable."""
    ok, err = check_db_connection()
    if not ok:
        st.error(
            "⚠️ **Database Connection Error**\n\n"
            f"Could not connect to PostgreSQL database.\n\n"
            f"**Details:** `{err}`\n\n"
            "Please ensure PostgreSQL is running and check your `.env` settings."
        )
        st.stop()


# ── Initialisation ────────────────────────────────────────────────────────────

def init_db() -> None:
    """
    Execute schema.sql against the configured database.
    Safe to call multiple times — all statements use IF NOT EXISTS.
    """
    if not _SCHEMA_FILE.exists():
        return
    sql = _SCHEMA_FILE.read_text()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


# ── Query helpers ─────────────────────────────────────────────────────────────

def execute(sql: str, params: tuple | dict | None = None) -> None:
    """Execute a write statement (INSERT / UPDATE / DELETE)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()


def fetch_one(
    sql: str, params: tuple | dict | None = None
) -> Optional[dict]:
    """Return the first matching row as a dict, or None."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def fetch_all(
    sql: str, params: tuple | dict | None = None
) -> list[dict]:
    """Return all matching rows as a list of dicts."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def fetch_scalar(sql: str, params: tuple | dict | None = None) -> Any:
    """Return the first column of the first row (for COUNT(*), etc.)."""
    row = fetch_one(sql, params)
    if row is None:
        return None
    return next(iter(row.values()))
