from datetime import datetime
from .db import get_connection


def record_settlement(
    person_id: int,
    amount_paise: int,
    settled_date: str,
    notes: str | None = None,
) -> int:
    """Record a settlement payment for a person."""
    connection = get_connection()
    now = datetime.now().isoformat()

    cursor = connection.execute(
        """
        INSERT INTO settlements (
            person_id, amount_paise, settled_date, notes, created_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            person_id,
            amount_paise,
            settled_date,
            notes.strip() if notes else None,
            now,
        ),
    )

    settlement_id = cursor.lastrowid
    connection.commit()
    connection.close()

    return settlement_id


def get_settlements_for_person(person_id: int) -> list[dict]:
    """Get all settlement history records for a specific person."""
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            s.id,
            s.settled_date,
            s.amount_paise,
            s.notes,
            s.created_at
        FROM settlements s
        WHERE s.person_id = ?
        ORDER BY s.settled_date DESC, s.id DESC
        """,
        (person_id,),
    ).fetchall()

    connection.close()

    return [
        {
            "id": row[0],
            "settled_date": row[1],
            "amount_paise": row[2],
            "notes": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]


def get_all_settlements() -> list[dict]:
    """Get complete settlement audit log across all people."""
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            s.id,
            s.settled_date,
            p.id,
            p.name,
            s.amount_paise,
            s.notes,
            s.created_at
        FROM settlements s
        JOIN people p ON p.id = s.person_id
        ORDER BY s.settled_date DESC, s.id DESC
        """,
    ).fetchall()

    connection.close()

    return [
        {
            "id": row[0],
            "settled_date": row[1],
            "person_id": row[2],
            "person_name": row[3],
            "amount_paise": row[4],
            "notes": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]


def get_total_settled_by_person() -> dict[int, int]:
    """Return a mapping of person_id -> total_settled_paise."""
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT person_id, SUM(amount_paise)
        FROM settlements
        GROUP BY person_id
        """,
    ).fetchall()

    connection.close()

    return {person_id: (total or 0) for person_id, total in rows}
