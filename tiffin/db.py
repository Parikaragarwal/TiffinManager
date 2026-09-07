import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".local" / "share" / "tiffin" / "tiffin.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    connection = get_connection()

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS consumption (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            meal TEXT NOT NULL CHECK (meal IN ('lunch', 'dinner')),
            person_id INTEGER NOT NULL,
            ate INTEGER NOT NULL CHECK (ate IN (0, 1)),
            description TEXT,
            price_paise INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            FOREIGN KEY (person_id)
                REFERENCES people(id)
                ON DELETE CASCADE,

            UNIQUE (date, meal, person_id)
        );

        CREATE TABLE IF NOT EXISTS settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            amount_paise INTEGER NOT NULL,
            settled_date TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,

            FOREIGN KEY (person_id)
                REFERENCES people(id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_consumption_date
        ON consumption(date);

        CREATE INDEX IF NOT EXISTS idx_consumption_person_date
        ON consumption(person_id, date);

        CREATE INDEX IF NOT EXISTS idx_settlements_person
        ON settlements(person_id);

        CREATE INDEX IF NOT EXISTS idx_settlements_date
        ON settlements(settled_date);
        """
    )

    connection.commit()
    connection.close()


def seed_people() -> None:
    connection = get_connection()

    people = [
        "Parikar",
        "Abhay",
        "Ashutosh",
        "Atharva",
    ]

    connection.executemany(
        "INSERT OR IGNORE INTO people (name) VALUES (?)",
        [(person,) for person in people],
    )

    connection.commit()
    connection.close()


def get_people() -> list[tuple[int, str]]:
    connection = get_connection()

    rows = connection.execute(
        "SELECT id, name FROM people ORDER BY id"
    ).fetchall()

    connection.close()

    return rows


def get_recorded_meals(record_date: str) -> set[str]:
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT DISTINCT meal
        FROM consumption
        WHERE date = ?
        """,
        (record_date,),
    ).fetchall()

    connection.close()

    return {row[0] for row in rows}


def get_ate_history(
    person_id: int,
    meal: str,
    limit: int = 10,
) -> list[bool]:
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT ate
        FROM consumption
        WHERE person_id = ?
          AND meal = ?
        ORDER BY date DESC, id DESC
        LIMIT ?
        """,
        (person_id, meal, limit),
    ).fetchall()

    connection.close()

    return [bool(row[0]) for row in rows]


def save_consumption(
    date: str,
    meal: str,
    person_id: int,
    ate: bool,
    description: str | None,
    price_paise: int | None,
) -> None:
    """Insert or update a consumption record for a person on a date and meal."""
    connection = get_connection()
    now = datetime.now().isoformat()

    connection.execute(
        """
        INSERT INTO consumption (
            date, meal, person_id, ate, description, price_paise, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date, meal, person_id) DO UPDATE SET
            ate = excluded.ate,
            description = excluded.description,
            price_paise = excluded.price_paise,
            updated_at = excluded.updated_at
        """,
        (
            date,
            meal,
            person_id,
            1 if ate else 0,
            description,
            price_paise,
            now,
            now,
        ),
    )

    connection.commit()
    connection.close()


def delete_consumption_record(record_date: str, meal: str | None = None) -> int:
    """Delete consumption records for a date (and optional specific meal). Returns deleted row count."""
    connection = get_connection()

    if meal:
        cursor = connection.execute(
            "DELETE FROM consumption WHERE date = ? AND meal = ?",
            (record_date, meal),
        )
    else:
        cursor = connection.execute(
            "DELETE FROM consumption WHERE date = ?",
            (record_date,),
        )

    deleted_count = cursor.rowcount
    connection.commit()
    connection.close()

    return deleted_count


def get_consumption_for_date(record_date: str) -> list[tuple]:
    """Get all consumption records for a single date."""
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            c.meal,
            p.id,
            p.name,
            c.ate,
            c.description,
            c.price_paise
        FROM consumption c
        JOIN people p ON p.id = c.person_id
        WHERE c.date = ?
        ORDER BY p.id, c.meal
        """,
        (record_date,),
    ).fetchall()

    connection.close()

    return rows


def get_consumption_between(
    start_date: str,
    end_date: str,
) -> list[tuple]:
    """Get all consumption records in [start_date, end_date] (inclusive)."""
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            c.date,
            c.meal,
            p.id,
            p.name,
            c.ate,
            c.description,
            c.price_paise
        FROM consumption c
        JOIN people p ON p.id = c.person_id
        WHERE c.date >= ?
          AND c.date <= ?
        ORDER BY c.date, c.meal, p.id
        """,
        (start_date, end_date),
    ).fetchall()

    connection.close()

    return rows
