from calendar import monthrange
from datetime import date
from collections import defaultdict

from .db import (
    get_connection,
    get_consumption_between,
    get_consumption_for_date,
    get_people,
)


def get_day_status(record_date: str) -> dict:
    """Return all recorded consumption for a particular date."""
    rows = get_consumption_for_date(record_date)

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
    """Calculate a complete report for a date range [start_date, end_date]."""
    rows = get_consumption_between(start_date, end_date)

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

    for (
        record_date,
        meal,
        person_id,
        name,
        ate,
        description,
        price_paise,
    ) in rows:
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
        meals[meal]["recorded"] += 1
        days[record_date][meal]["recorded"] = True

        if not ate:
            continue

        cost = price_paise or 0
        person["tiffins"] += 1
        person[meal] += 1
        person["cost_paise"] += cost

        desc_clean = (description or "").strip().lower()
        if desc_clean == "special":
            person["special"] += 1
            specials.append(
                {
                    "date": record_date,
                    "meal": meal,
                    "person_id": person_id,
                    "name": name,
                    "price_paise": cost,
                }
            )
            meals[meal]["special"] += 1
        else:
            person["regular"] += 1
            meals[meal]["regular"] += 1

        meals[meal]["tiffins"] += 1
        meals[meal]["cost_paise"] += cost

        days[record_date][meal]["tiffins"] += 1
        days[record_date][meal]["cost_paise"] += cost

    total_tiffins = sum(p["tiffins"] for p in people.values())
    total_regular = sum(p["regular"] for p in people.values())
    total_special = sum(p["special"] for p in people.values())
    total_cost_paise = sum(p["cost_paise"] for p in people.values())

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


def get_missing_records(year: int | None = None, month: int | None = None) -> list[dict]:
    """
    Find dates in the specified month (or current month) that have missing lunch or dinner records.
    Only checks up to today's date if checking current month.
    """
    today = date.today()
    if year is None or month is None:
        year, month = today.year, today.month

    start_date = date(year, month, 1).isoformat()
    _, num_days = monthrange(year, month)
    end_day = min(num_days, today.day) if (year == today.year and month == today.month) else num_days
    end_date = date(year, month, end_day).isoformat()

    rows = get_consumption_between(start_date, end_date)

    recorded_days = defaultdict(set)
    for record_date, meal, _, _, _, _, _ in rows:
        recorded_days[record_date].add(meal)

    missing = []
    current_day = date(year, month, 1)
    stop_day = date(year, month, end_day)

    while current_day <= stop_day:
        d_str = current_day.isoformat()
        meals_present = recorded_days[d_str]

        missing_meals = []
        if "lunch" not in meals_present:
            missing_meals.append("lunch")
        if "dinner" not in meals_present:
            missing_meals.append("dinner")

        if missing_meals:
            missing.append({
                "date": d_str,
                "missing_meals": missing_meals,
            })

        current_day += date.resolution  # timedelta(days=1)

    return missing


def parse_date_range(period_str: str | None = None) -> tuple[str, str, str]:
    """
    Parse a period string into (start_date, end_date, display_label).
    Defaults to current month if None or empty.
    Supports:
        "2026-09"
        "september" / "sep"
        "2026-09-01:2026-09-30"
    """
    today = date.today()
    if not period_str:
        year, month = today.year, today.month
        _, last_day = monthrange(year, month)
        start = date(year, month, 1).isoformat()
        end = date(year, month, last_day).isoformat()
        label = date(year, month, 1).strftime("%B %Y")
        return start, end, label

    period_str = period_str.strip().lower()

    if ":" in period_str:
        parts = period_str.split(":")
        start = parts[0].strip()
        end = parts[1].strip()
        label = f"{start} to {end}"
        return start, end, label

    # YYYY-MM
    if len(period_str) == 7 and period_str[4] == "-":
        try:
            year, month = int(period_str[:4]), int(period_str[5:])
            _, last_day = monthrange(year, month)
            start = date(year, month, 1).isoformat()
            end = date(year, month, last_day).isoformat()
            label = date(year, month, 1).strftime("%B %Y")
            return start, end, label
        except ValueError:
            pass

    # Month name e.g. "september"
    try:
        dt = datetime.strptime(period_str, "%B")
        month = dt.month
        year = today.year
        _, last_day = monthrange(year, month)
        start = date(year, month, 1).isoformat()
        end = date(year, month, last_day).isoformat()
        label = date(year, month, 1).strftime("%B %Y")
        return start, end, label
    except ValueError:
        pass

    try:
        dt = datetime.strptime(period_str, "%b")
        month = dt.month
        year = today.year
        _, last_day = monthrange(year, month)
        start = date(year, month, 1).isoformat()
        end = date(year, month, last_day).isoformat()
        label = date(year, month, 1).strftime("%B %Y")
        return start, end, label
    except ValueError:
        pass

    # Default fallback: assume current month
    year, month = today.year, today.month
    _, last_day = monthrange(year, month)
    return date(year, month, 1).isoformat(), date(year, month, last_day).isoformat(), f"{today.strftime('%B %Y')}"