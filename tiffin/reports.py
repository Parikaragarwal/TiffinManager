from calendar import monthrange
from datetime import date, datetime, timedelta
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
    """Find the date range covering all unsettled dues period up to today."""
    connection = get_connection()
    earliest_row = connection.execute("SELECT MIN(date) FROM consumption").fetchone()
    connection.close()

    today_str = date.today().isoformat()
    if not earliest_row or not earliest_row[0]:
        start_date = date(date.today().year, date.today().month, 1).isoformat()
        return start_date, today_str, "Current Month"

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
    """Calculate a massively detailed report for a date range [start_date, end_date]."""
    rows = get_consumption_between(start_date, end_date)
    all_people = get_people()

    people = {
        p_id: {
            "name": name,
            "lunch": 0,
            "dinner": 0,
            "tiffins": 0,
            "special": 0,
            "cost_paise": 0,
        }
        for p_id, name in all_people
    }

    recorded_lunches = set()
    recorded_dinners = set()

    lunch_stats = {"tiffins": 0, "regular": 0, "special": 0, "cost_paise": 0}
    dinner_stats = {"tiffins": 0, "regular": 0, "special": 0, "cost_paise": 0}

    daily_map = defaultdict(
        lambda: {
            "lunch_tiffins": 0,
            "dinner_tiffins": 0,
            "total_tiffins": 0,
            "cost_paise": 0,
            "lunch_recorded": False,
            "dinner_recorded": False,
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
        if meal == "lunch":
            recorded_lunches.add(record_date)
            daily_map[record_date]["lunch_recorded"] = True
        else:
            recorded_dinners.add(record_date)
            daily_map[record_date]["dinner_recorded"] = True

        if not ate:
            continue

        cost = price_paise or 0
        desc_clean = (description or "").strip().lower()
        is_special = (desc_clean == "special")

        # Person stats
        p_entry = people[person_id]
        p_entry[meal] += 1
        p_entry["tiffins"] += 1
        p_entry["cost_paise"] += cost
        if is_special:
            p_entry["special"] += 1

        # Meal stats
        m_target = lunch_stats if meal == "lunch" else dinner_stats
        m_target["tiffins"] += 1
        m_target["cost_paise"] += cost
        if is_special:
            m_target["special"] += 1
        else:
            m_target["regular"] += 1

        # Daily stats
        d_target = daily_map[record_date]
        if meal == "lunch":
            d_target["lunch_tiffins"] += 1
        else:
            d_target["dinner_tiffins"] += 1
        d_target["total_tiffins"] += 1
        d_target["cost_paise"] += cost

        if is_special:
            specials.append({
                "date": record_date,
                "meal": meal,
                "person_id": person_id,
                "name": name,
                "price_paise": cost,
            })

    total_tiffins = lunch_stats["tiffins"] + dinner_stats["tiffins"]
    total_regular = lunch_stats["regular"] + dinner_stats["regular"]
    total_special = lunch_stats["special"] + dinner_stats["special"]
    total_cost_paise = lunch_stats["cost_paise"] + dinner_stats["cost_paise"]
    avg_per_tiffin_paise = int(total_cost_paise / total_tiffins) if total_tiffins > 0 else 0

    # Unrecorded meals detection across all dates in range
    unrecorded = []
    try:
        cur_d = date.fromisoformat(start_date)
        end_d = date.fromisoformat(end_date)
        today_d = date.today()
        max_d = min(end_d, today_d)

        while cur_d <= max_d:
            d_str = cur_d.isoformat()
            if d_str not in recorded_lunches:
                unrecorded.append({"date": d_str, "meal": "lunch"})
            if d_str not in recorded_dinners:
                unrecorded.append({"date": d_str, "meal": "dinner"})
            cur_d += timedelta(days=1)
    except ValueError:
        pass

    return {
        "overview": {
            "recorded_lunches": len(recorded_lunches),
            "recorded_dinners": len(recorded_dinners),
            "total_tiffins": total_tiffins,
            "regular": total_regular,
            "special": total_special,
            "total_cost_paise": total_cost_paise,
            "avg_per_tiffin_paise": avg_per_tiffin_paise,
        },
        "lunch_vs_dinner": {
            "lunch": lunch_stats,
            "dinner": dinner_stats,
        },
        "people": people,
        "daily": dict(sorted(daily_map.items())),
        "specials": specials,
        "unrecorded": unrecorded,
    }


def get_missing_records(year: int | None = None, month: int | None = None) -> list[dict]:
    """Find dates in current/given month that have missing lunch or dinner records."""
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

        current_day += timedelta(days=1)

    return missing


def parse_date_range(period_str: str | None = None, scope: str = "unsettled") -> tuple[str, str, str]:
    """Parse period string or scope into (start_date, end_date, display_label)."""
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
        return get_unsettled_date_range()

    period_str = period_str.strip().lower()

    if ":" in period_str:
        parts = period_str.split(":")
        start = parts[0].strip()
        end = parts[1].strip()
        label = f"{start} to {end}"
        return start, end, label

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

    return get_unsettled_date_range()