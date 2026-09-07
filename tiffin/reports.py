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


def get_unsettled_date_range() -> tuple[str, str, str]:
    """
    Find the date range covering all unsettled dues period up to today.
    Identifies the earliest recorded date where total consumption charges exceeded total settlements.
    """
    connection = get_connection()

    # Find earliest date in consumption
    earliest_row = connection.execute("SELECT MIN(date) FROM consumption").fetchone()
    connection.close()

    today_str = date.today().isoformat()
    if not earliest_row or not earliest_row[0]:
        start_date = date(date.today().year, date.today().month, 1).isoformat()
        return start_date, today_str, "Current Month (No Prior Records)"

    start_date = earliest_row[0]
    return start_date, today_str, f"Unsettled Dues Period ({start_date} to {today_str})"


def get_all_time_date_range() -> tuple[str, str, str]:
    """Find the full date range for all records in the database."""
    connection = get_connection()
    row = connection.execute("SELECT MIN(date), MAX(date) FROM consumption").fetchone()
    connection.close()

    today_str = date.today().isoformat()
    if not row or not row[0]:
        return today_str, today_str, "All Time (Empty DB)"

    start_date = row[0]
    end_date = row[1] or today_str
    return start_date, end_date, f"All Time History ({start_date} to {end_date})"


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

        current_day += date.resolution

    return missing


def parse_date_range(period_str: str | None = None, scope: str = "unsettled") -> tuple[str, str, str]:
    """
    Parse a period string or scope into (start_date, end_date, display_label).
    If no period_str provided:
        - scope="unsettled" (default) -> earliest un-cleared consumption to today
        - scope="month"               -> start of current month to end of current month
        - scope="all"                 -> earliest record to latest record in DB
    """
    today = date.today()
    if not period_str:
        if scope == "all":
            return get_all_time_date_range()
        if scope == "month":
            year, month = today.year, today.month
            _, last_day = monthrange(year, month)
            start = date(year, month, 1).isoformat()
            end = date(year, month, last_day).isoformat()
            label = date(year, month, 1).strftime("%B %Y")
            return start, end, label
        # Default: unsettled period
        return get_unsettled_date_range()

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

    # Fallback to unsettled range
    return get_unsettled_date_range()