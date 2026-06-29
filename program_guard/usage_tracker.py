"""Historial de programas usados (últimos 7 días)."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import psutil

from program_guard.config_manager import CONFIG_DIR
from program_guard.game_detection import is_likely_game

DB_PATH = CONFIG_DIR / "usage.db"
RETENTION_DAYS = 7


class UsageTracker:
    def __init__(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        self._seen_pids: dict[int, tuple[str, str, float]] = {}

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS process_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exe_name TEXT NOT NULL,
                exe_path TEXT,
                started_at REAL NOT NULL,
                ended_at REAL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_exe ON process_sessions(exe_name)"
        )
        self._conn.commit()

    def scan_running(self, tagged_games: set[str] | None = None) -> list[dict]:
        now = time.time()
        running: list[dict] = []
        active_pids: set[int] = set()

        for proc in psutil.process_iter(["pid", "name", "exe", "create_time"]):
            try:
                pid = proc.info["pid"]
                name = (proc.info.get("name") or "").lower()
                exe_path = proc.info.get("exe") or ""
                if not name or pid <= 4:
                    continue
                active_pids.add(pid)
                running.append(
                    {
                        "exe_name": name,
                        "exe_path": exe_path,
                        "is_game": is_likely_game(name, exe_path, tagged_games),
                        "pid": pid,
                    }
                )
                if pid not in self._seen_pids:
                    self._seen_pids[pid] = (name, exe_path, now)
                    self._conn.execute(
                        "INSERT INTO process_sessions (exe_name, exe_path, started_at) VALUES (?, ?, ?)",
                        (name, exe_path, now),
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        ended = [pid for pid in self._seen_pids if pid not in active_pids]
        for pid in ended:
            name, _path, started = self._seen_pids.pop(pid)
            self._conn.execute(
                "UPDATE process_sessions SET ended_at = ? WHERE exe_name = ? AND started_at = ? AND ended_at IS NULL",
                (now, name, started),
            )
        self._conn.commit()
        self._purge_old()
        return running

    def _purge_old(self) -> None:
        cutoff = time.time() - RETENTION_DAYS * 86400
        self._conn.execute("DELETE FROM process_sessions WHERE started_at < ?", (cutoff,))
        self._conn.commit()

    def programs_last_7_days(self, tagged_games: set[str] | None = None) -> list[dict]:
        cutoff = time.time() - RETENTION_DAYS * 86400
        rows = self._conn.execute(
            """
            SELECT exe_name, exe_path,
                   COUNT(*) AS sessions,
                   SUM(COALESCE(ended_at, ?) - started_at) AS seconds
            FROM process_sessions
            WHERE started_at >= ?
            GROUP BY exe_name
            ORDER BY seconds DESC
            """,
            (time.time(), cutoff),
        ).fetchall()

        result = []
        for row in rows:
            exe = row["exe_name"]
            path = row["exe_path"] or ""
            seconds = max(0, int(row["seconds"] or 0))
            game = is_likely_game(exe, path, tagged_games)
            result.append(
                {
                    "exe_name": exe,
                    "exe_path": path,
                    "sessions": int(row["sessions"]),
                    "minutes": round(seconds / 60, 1),
                    "is_game": game,
                    "category": "Juego" if game else "Programa",
                    "frequent": int(row["sessions"]) >= 5 or seconds >= 3600,
                }
            )
        return result

    def close(self) -> None:
        self._conn.close()
