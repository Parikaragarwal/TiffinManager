import json
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .db import DB_PATH, get_connection, initialize_database


def get_backup_dir() -> Path:
    backup_dir = DB_PATH.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def export_db_to_dict() -> dict[str, Any]:
    """Export complete database contents to a JSON-serializable dictionary."""
    if not DB_PATH.exists():
        return {"people": [], "consumption": [], "settlements": []}

    connection = get_connection()

    people_rows = connection.execute("SELECT id, name FROM people ORDER BY id").fetchall()
    people = [{"id": r[0], "name": r[1]} for r in people_rows]

    consumption_rows = connection.execute(
        """
        SELECT id, date, meal, person_id, ate, description, price_paise, created_at, updated_at
        FROM consumption ORDER BY id
        """
    ).fetchall()
    consumption = [
        {
            "id": r[0],
            "date": r[1],
            "meal": r[2],
            "person_id": r[3],
            "ate": r[4],
            "description": r[5],
            "price_paise": r[6],
            "created_at": r[7],
            "updated_at": r[8],
        }
        for r in consumption_rows
    ]

    settlement_rows = connection.execute(
        """
        SELECT id, person_id, amount_paise, settled_date, notes, created_at
        FROM settlements ORDER BY id
        """
    ).fetchall()
    settlements = [
        {
            "id": r[0],
            "person_id": r[1],
            "amount_paise": r[2],
            "settled_date": r[3],
            "notes": r[4],
            "created_at": r[5],
        }
        for r in settlement_rows
    ]

    connection.close()

    return {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "people": people,
        "consumption": consumption,
        "settlements": settlements,
    }


def export_db_to_json() -> str:
    """Return JSON string representation of entire database."""
    return json.dumps(export_db_to_dict(), indent=2)


def restore_db_from_dict(data: dict[str, Any]) -> None:
    """Restore database from a dictionary containing serialized records."""
    initialize_database()
    connection = get_connection()

    connection.execute("DELETE FROM settlements")
    connection.execute("DELETE FROM consumption")
    connection.execute("DELETE FROM people")

    for p in data.get("people", []):
        connection.execute(
            "INSERT OR REPLACE INTO people (id, name) VALUES (?, ?)",
            (p["id"], p["name"]),
        )

    for c in data.get("consumption", []):
        connection.execute(
            """
            INSERT OR REPLACE INTO consumption (
                id, date, meal, person_id, ate, description, price_paise, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                c["id"],
                c["date"],
                c["meal"],
                c["person_id"],
                c["ate"],
                c.get("description"),
                c.get("price_paise"),
                c.get("created_at", datetime.now().isoformat()),
                c.get("updated_at", datetime.now().isoformat()),
            ),
        )

    for s in data.get("settlements", []):
        connection.execute(
            """
            INSERT OR REPLACE INTO settlements (
                id, person_id, amount_paise, settled_date, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                s["id"],
                s["person_id"],
                s["amount_paise"],
                s["settled_date"],
                s.get("notes"),
                s.get("created_at", datetime.now().isoformat()),
            ),
        )

    connection.commit()
    connection.close()


def restore_db_from_file(filepath: str | Path) -> None:
    """Restore database from a `.db` SQLite file or `.json` file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Backup file not found: {path}")

    if path.suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        restore_db_from_dict(data)
    else:
        # SQLite db binary file
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, DB_PATH)


def create_db_backup(destination_path: str | Path | None = None) -> Path:
    """Create timestamped SQLite & JSON backups in backups directory or custom path."""
    b_dir = get_backup_dir()
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    if destination_path:
        target = Path(destination_path)
    else:
        target = b_dir / f"tiffin_backup_{now_str}.json"

    json_str = export_db_to_json()
    with open(target, "w", encoding="utf-8") as f:
        f.write(json_str)

    # Also update latest copy
    latest_json = b_dir / "tiffin_backup_latest.json"
    with open(latest_json, "w", encoding="utf-8") as f:
        f.write(json_str)

    if DB_PATH.exists():
        latest_db = b_dir / "tiffin_backup_latest.db"
        shutil.copy2(DB_PATH, latest_db)

    # If TIFFIN_CLOUD_DIR is configured in env, copy to cloud directory
    cloud_dir_str = os.environ.get("TIFFIN_CLOUD_DIR")
    if cloud_dir_str:
        try:
            c_path = Path(cloud_dir_str)
            if c_path.exists() and c_path.is_dir():
                shutil.copy2(target, c_path / target.name)
                shutil.copy2(latest_json, c_path / "tiffin_backup_latest.json")
        except Exception:
            pass

    return target


def load_env_file() -> None:
    """Auto-load variables from local .env or ~/.local/share/tiffin/.env if present."""
    search_paths = [
        Path.cwd() / ".env",
        Path.home() / ".local" / "share" / "tiffin" / ".env",
        Path(__file__).parent.parent / ".env",
    ]
    for env_path in search_paths:
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass


def auto_backup() -> None:
    """Automatic background backup triggered on any database mutation."""
    load_env_file()
    try:
        create_db_backup()
    except Exception:
        pass

    # If TIFFIN_SERVER_URL is set (e.g. http://YOUR_VPS_IP:8765), sync directly over HTTP POST
    server_url = os.environ.get("TIFFIN_SERVER_URL")
    if server_url:
        try:
            import urllib.request
            data = export_db_to_dict()
            json_bytes = json.dumps(data).encode("utf-8")
            req_url = f"{server_url.rstrip('/')}/api/sync"
            req = urllib.request.Request(
                req_url,
                data=json_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Tiffin-Token": os.environ.get("TIFFIN_SYNC_KEY", ""),
                },
                method="POST",
            )
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass
