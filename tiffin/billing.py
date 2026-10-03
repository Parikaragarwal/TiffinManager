from .db import get_people, get_connection
from .settlement_db import get_total_settled_by_person, get_settlements_for_person


def calculate_fifo_tiffin_status(person_id: int) -> tuple[list[dict], int]:
    """
    Calculate FIFO settlement status for itemized consumption of a person.
    Returns:
       (tagged_meals, remaining_credit_paise)
       Where each meal in tagged_meals has:
         date, meal, ate, description, price_paise, status ('settled', 'partially_settled', 'unsettled'),
         amount_settled_paise, remaining_due_paise
    """
    connection = get_connection()
    consumption_rows = connection.execute(
        """
        SELECT id, date, meal, ate, description, price_paise
        FROM consumption
        WHERE person_id = ?
        ORDER BY date ASC, meal ASC, id ASC
        """,
        (person_id,),
    ).fetchall()
    connection.close()

    settlements = get_settlements_for_person(person_id)
    # Sum total settlement funds available (in chronological order)
    available_funds = sum(s["amount_paise"] for s in settlements)

    tagged_meals = []
    for c_id, record_date, meal, ate, description, price_paise in consumption_rows:
        if not ate:
            continue

        cost = price_paise or 0
        if cost == 0:
            status = "settled"
            settled_amount = 0
            due_amount = 0
        elif available_funds >= cost:
            status = "settled"
            settled_amount = cost
            due_amount = 0
            available_funds -= cost
        elif available_funds > 0:
            status = "partially_settled"
            settled_amount = available_funds
            due_amount = cost - available_funds
            available_funds = 0
        else:
            status = "unsettled"
            settled_amount = 0
            due_amount = cost

        tagged_meals.append(
            {
                "id": c_id,
                "date": record_date,
                "meal": meal,
                "ate": True,
                "description": description or "Regular",
                "price_paise": cost,
                "status": status,
                "amount_settled_paise": settled_amount,
                "remaining_due_paise": due_amount,
            }
        )

    return tagged_meals, available_funds


def get_person_balances() -> list[dict]:
    """
    Calculate current account balances for all people.
    Returns a list of dicts with:
      id, name, tiffins, total_cost_paise, total_settled_paise, pending_paise
    """
    people = get_people()
    settled_map = get_total_settled_by_person()

    connection = get_connection()
    # Query consumption totals per person
    rows = connection.execute(
        """
        SELECT
            person_id,
            COUNT(CASE WHEN ate = 1 THEN 1 END) as tiffins,
            SUM(CASE WHEN ate = 1 THEN price_paise ELSE 0 END) as total_cost
        FROM consumption
        GROUP BY person_id
        """,
    ).fetchall()
    connection.close()

    consumption_map = {
        row[0]: {
            "tiffins": row[1] or 0,
            "total_cost_paise": row[2] or 0,
        }
        for row in rows
    }

    balances = []
    for person_id, name in people:
        c_info = consumption_map.get(person_id, {"tiffins": 0, "total_cost_paise": 0})
        total_cost = c_info["total_cost_paise"]
        total_settled = settled_map.get(person_id, 0)
        pending = total_cost - total_settled

        balances.append(
            {
                "person_id": person_id,
                "name": name,
                "tiffins": c_info["tiffins"],
                "total_cost_paise": total_cost,
                "total_settled_paise": total_settled,
                "pending_paise": pending,
            }
        )

    return balances



def get_person_bill(person_id: int) -> dict:
    """Generate detailed itemized bill and settlement balance for a person with FIFO statuses."""
    connection = get_connection()

    person_row = connection.execute(
        "SELECT id, name FROM people WHERE id = ?", (person_id,)
    ).fetchone()
    connection.close()

    if not person_row:
        raise ValueError(f"Person with ID {person_id} does not exist.")

    p_id, name = person_row

    meals_detail, remaining_credit = calculate_fifo_tiffin_status(person_id)
    settlements = get_settlements_for_person(person_id)

    total_cost_paise = sum(m["price_paise"] for m in meals_detail)
    tiffins_count = len(meals_detail)
    total_settled_paise = sum(s["amount_paise"] for s in settlements)
    pending_paise = total_cost_paise - total_settled_paise

    return {
        "person_id": p_id,
        "name": name,
        "tiffins_count": tiffins_count,
        "total_cost_paise": total_cost_paise,
        "settlements": settlements,
        "total_settled_paise": total_settled_paise,
        "pending_paise": pending_paise,
        "remaining_credit_paise": remaining_credit,
        "meals_detail": meals_detail,
    }



def get_overall_bill() -> dict:
    """Generate overall summary bill across all people."""
    balances = get_person_balances()

    total_tiffins = sum(b["tiffins"] for b in balances)
    total_cost_paise = sum(b["total_cost_paise"] for b in balances)
    total_settled_paise = sum(b["total_settled_paise"] for b in balances)
    total_pending_paise = total_cost_paise - total_settled_paise

    return {
        "balances": balances,
        "total_tiffins": total_tiffins,
        "total_cost_paise": total_cost_paise,
        "total_settled_paise": total_settled_paise,
        "total_pending_paise": total_pending_paise,
    }
