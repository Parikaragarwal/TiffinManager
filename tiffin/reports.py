from .db import (
    get_connection,
    get_consumption_between,
)

from collections import defaultdict


def get_day_status(record_date: str) -> dict:
    """Return all recorded consumption for a particular date."""

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

    result = {
        "lunch": {},
        "dinner": {},
    }

    for meal, person_id, name, ate, description, price_paise in rows:
        result[meal][person_id] = {
            "name": name,
            "ate": bool(ate),
            "description": description,
            "price_paise": price_paise,
        }

    return result

def get_month_report(
    start_date: str,
    end_date: str,
) -> dict:
    """Calculate a complete report for a date range."""

    rows = get_consumption_between(
        start_date,
        end_date,
    )

    # ---------------------------------------------------------
    # Basic containers
    # ---------------------------------------------------------

    people = {}

    meals = {
        "lunch": {
            "recorded": 0,
            "tiffins": 0,
            "regular": 0,
            "special": 0,
            "cost_paise": 0,
        },
        "dinner": {
            "recorded": 0,
            "tiffins": 0,
            "regular": 0,
            "special": 0,
            "cost_paise": 0,
        },
    }

    days = defaultdict(
        lambda: {
            "lunch": {
                "recorded": False,
                "tiffins": 0,
                "cost_paise": 0,
            },
            "dinner": {
                "recorded": False,
                "tiffins": 0,
                "cost_paise": 0,
            },
        }
    )

    specials = []

    # ---------------------------------------------------------
    # Process records
    # ---------------------------------------------------------

    for (
        record_date,
        meal,
        person_id,
        name,
        ate,
        description,
        price_paise,
    ) in rows:

        # Create person entry if necessary.
        if person_id not in people:
            people[person_id] = {
                "name": name,
                "tiffins": 0,
                "lunch": 0,
                "dinner": 0,
                "regular": 0,
                "special": 0,
                "cost_paise": 0,
            }

        person = people[person_id]

        # A row existing means this meal was recorded.
        meals[meal]["recorded"] += 1
        days[record_date][meal]["recorded"] = True

        # Didn't eat → nothing else to calculate.
        if not ate:
            continue

        # -----------------------------------------------------
        # Person statistics
        # -----------------------------------------------------

        person["tiffins"] += 1
        person[meal] += 1
        person["cost_paise"] += price_paise

        # -----------------------------------------------------
        # Regular / Special
        # -----------------------------------------------------

        if description.strip().lower() == "special":
            person["special"] += 1

            specials.append(
                {
                    "date": record_date,
                    "meal": meal,
                    "person_id": person_id,
                    "name": name,
                    "price_paise": price_paise,
                }
            )

            meals[meal]["special"] += 1

        else:
            person["regular"] += 1
            meals[meal]["regular"] += 1

        # -----------------------------------------------------
        # Meal statistics
        # -----------------------------------------------------

        meals[meal]["tiffins"] += 1
        meals[meal]["cost_paise"] += price_paise

        # -----------------------------------------------------
        # Daily statistics
        # -----------------------------------------------------

        days[record_date][meal]["tiffins"] += 1
        days[record_date][meal]["cost_paise"] += price_paise

    # ---------------------------------------------------------
    # Derived totals
    # ---------------------------------------------------------

    total_tiffins = sum(
        person["tiffins"]
        for person in people.values()
    )

    total_regular = sum(
        person["regular"]
        for person in people.values()
    )

    total_special = sum(
        person["special"]
        for person in people.values()
    )

    total_cost_paise = sum(
        person["cost_paise"]
        for person in people.values()
    )

    return {
        "overview": {
            "tiffins": total_tiffins,
            "regular": total_regular,
            "special": total_special,
            "cost_paise": total_cost_paise,
        },
        "meals": dict(meals),
        "people": people,
        "days": dict(days),
        "specials": specials,
    }