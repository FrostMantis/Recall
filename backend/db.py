"""
MariaDB connection pool and schema bootstrap.
get_db() returns a context-manager-aware connection wrapper.
init_db() is idempotent — safe to call on every startup.
"""

import os
import queue
from pathlib import Path

import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

_SCHEMA = Path(__file__).parent.parent / "schema.sql"

_DB_CONFIG = dict(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", ""),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "recall_db"),
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=False,
    charset="utf8mb4",
)

_POOL: queue.Queue = queue.Queue(maxsize=10)


def _new_raw_conn() -> pymysql.connections.Connection:
    return pymysql.connect(**_DB_CONFIG)


def _acquire() -> pymysql.connections.Connection:
    try:
        conn = _POOL.get_nowait()
        conn.ping(reconnect=True)
        return conn
    except queue.Empty:
        return _new_raw_conn()


def _release(conn: pymysql.connections.Connection) -> None:
    try:
        _POOL.put_nowait(conn)
    except queue.Full:
        conn.close()


class _Conn:
    """Thin wrapper exposing the subset used by db.py / ops.py / main.py."""

    def __init__(self):
        self._conn = _acquire()

    # ── context manager ──────────────────────────────────────────────────
    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()
        _release(self._conn)

    # ── query helpers ─────────────────────────────────────────────────────
    def execute(self, sql: str, params=None):
        cur = self._conn.cursor()
        cur.execute(sql, params or ())
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()


def get_db() -> _Conn:
    return _Conn()


def init_db() -> None:
    schema = _SCHEMA.read_text()
    # MariaDB doesn't support "CREATE INDEX IF NOT EXISTS" until 10.1.4,
    # but does support it since 10.1.4+; split and run statement by statement.
    statements = [s.strip() for s in schema.split(";") if s.strip()]
    conn = _new_raw_conn()
    try:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()
    finally:
        conn.close()
