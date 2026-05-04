import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "asthma.db"


def _ensure_db_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def _connect():
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS patient (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                duration_years REAL NOT NULL,
                medications TEXT NOT NULL,
                triggers TEXT NOT NULL,
                severity TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                heart_rate INTEGER NOT NULL,
                breathing_rate INTEGER NOT NULL,
                spo2 REAL NOT NULL,
                aqi INTEGER NOT NULL,
                active_triggers TEXT NOT NULL,
                physical_stress INTEGER NOT NULL,
                status TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                reasons TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                status TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                reasons TEXT NOT NULL
            );
            """
        )


def save_patient(profile: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO patient (id, name, age, gender, duration_years,
                                 medications, triggers, severity, updated_at)
            VALUES (1, :name, :age, :gender, :duration_years,
                    :medications, :triggers, :severity, :updated_at)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                age = excluded.age,
                gender = excluded.gender,
                duration_years = excluded.duration_years,
                medications = excluded.medications,
                triggers = excluded.triggers,
                severity = excluded.severity,
                updated_at = excluded.updated_at
            """,
            {
                "name": profile["name"],
                "age": profile["age"],
                "gender": profile["gender"],
                "duration_years": profile["duration_years"],
                "medications": profile["medications"],
                "triggers": json.dumps(profile["triggers"]),
                "severity": profile["severity"],
                "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
            },
        )


def load_patient() -> Optional[dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM patient WHERE id = 1").fetchone()
    if row is None:
        return None
    data = dict(row)
    data["triggers"] = json.loads(data["triggers"])
    return data


def save_reading(reading: dict[str, Any]) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO readings (ts, heart_rate, breathing_rate, spo2, aqi,
                                  active_triggers, physical_stress,
                                  status, risk_score, reasons)
            VALUES (:ts, :heart_rate, :breathing_rate, :spo2, :aqi,
                    :active_triggers, :physical_stress,
                    :status, :risk_score, :reasons)
            """,
            {
                "ts": reading["ts"],
                "heart_rate": reading["heart_rate"],
                "breathing_rate": reading["breathing_rate"],
                "spo2": reading["spo2"],
                "aqi": reading["aqi"],
                "active_triggers": json.dumps(reading["active_triggers"]),
                "physical_stress": int(reading["physical_stress"]),
                "status": reading["status"],
                "risk_score": reading["risk_score"],
                "reasons": json.dumps(reading["reasons"]),
            },
        )
        return cur.lastrowid or 0


def save_alert(reading: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO alerts (ts, status, risk_score, reasons)
            VALUES (:ts, :status, :risk_score, :reasons)
            """,
            {
                "ts": reading["ts"],
                "status": reading["status"],
                "risk_score": reading["risk_score"],
                "reasons": json.dumps(reading["reasons"]),
            },
        )


def load_readings(limit: int = 200) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM readings ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for row in rows:
        d = dict(row)
        d["active_triggers"] = json.loads(d["active_triggers"])
        d["reasons"] = json.loads(d["reasons"])
        out.append(d)
    return out


def load_alerts(limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for row in rows:
        d = dict(row)
        d["reasons"] = json.loads(d["reasons"])
        out.append(d)
    return out


def clear_history() -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM readings")
        conn.execute("DELETE FROM alerts")
