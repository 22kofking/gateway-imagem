"""Banco de jobs. SQLite para começar; a interface é pequena para trocar por Postgres depois."""

import json
import sqlite3
import threading
import time

from app.config import settings

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    app TEXT NOT NULL,
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    route TEXT NOT NULL,
    provider_job_id TEXT NOT NULL,
    status TEXT NOT NULL,
    images TEXT,
    error TEXT,
    cost_usd REAL,
    created_at REAL NOT NULL,
    finished_at REAL
);
CREATE INDEX IF NOT EXISTS jobs_app_created ON jobs (app, created_at);
"""


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(settings.db_path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
    return _conn


def reset() -> None:
    """Fecha a conexão (usado nos testes para trocar de arquivo)."""
    global _conn
    if _conn is not None:
        _conn.close()
    _conn = None


def insert_job(job_id: str, app: str, model: str, provider: str, route: dict, provider_job_id: str) -> None:
    with _lock:
        conn().execute(
            "INSERT INTO jobs (id, app, model, provider, route, provider_job_id, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, 'running', ?)",
            (job_id, app, model, provider, json.dumps(route), provider_job_id, time.time()),
        )
        conn().commit()


def get_job(job_id: str, app: str) -> sqlite3.Row | None:
    with _lock:
        return conn().execute("SELECT * FROM jobs WHERE id = ? AND app = ?", (job_id, app)).fetchone()


def finish_job(job_id: str, status: str, images: list[str], error: str | None, cost_usd: float | None) -> None:
    with _lock:
        conn().execute(
            "UPDATE jobs SET status = ?, images = ?, error = ?, cost_usd = ?, finished_at = ?"
            " WHERE id = ? AND status = 'running'",
            (status, json.dumps(images), error, cost_usd, time.time(), job_id),
        )
        conn().commit()


def count_since(app: str, since: float) -> int:
    """Pedidos do app desde `since`, menos os que falharam (falha não conta no limite)."""
    with _lock:
        row = conn().execute(
            "SELECT COUNT(*) FROM jobs WHERE app = ? AND created_at >= ? AND status != 'failed'",
            (app, since),
        ).fetchone()
    return row[0]


def usage(app: str, since: float) -> list[dict]:
    with _lock:
        rows = conn().execute(
            "SELECT model, provider, COUNT(*) AS imagens, ROUND(SUM(COALESCE(cost_usd, 0)), 4) AS custo_usd"
            " FROM jobs WHERE app = ? AND status = 'succeeded' AND created_at >= ?"
            " GROUP BY model, provider ORDER BY model",
            (app, since),
        ).fetchall()
    return [dict(r) for r in rows]
