from datetime import date, datetime, timedelta, time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import typer

DEFAULT_PRICE_PAISE = 7000


def get_current_meal() -> str:
    """Return the default meal based on the current time."""
    now = datetime.now().time()
    if now < time(15, 0):
        return "lunch"
    return "dinner"


def get_learned_ate_default(history: list[bool]) -> bool:
    """
    Decide whether Ate? should default to Yes or No.
    Defaults to True if there are fewer than 3 previous records.
    """
    if len(history) < 3:
        return True

    ate_count = sum(history)
    return ate_count > len(history) / 2


def parse_date(value: str) -> str:
    """
    Convert friendly date input into YYYY-MM-DD.

    Supported formats:
        "" / "today"   -> today's date
        "yesterday"     -> yesterday's date
        "2"            -> 2nd of current month/year
        "2/9"          -> 2nd September of current year
        "2/9/2026"     -> 2nd September 2026
        "2026-09-02"   -> explicit ISO date
    """
    value = value.strip().lower()
    today = date.today()

    if value == "" or value == "today":
        return today.isoformat()

    if value == "yesterday":
        return (today - timedelta(days=1)).isoformat()

    # Just a day number
    if value.isdigit():
        day = int(value)
        if not 1 <= day <= 31:
            raise ValueError("Day must be between 1 and 31.")
        try:
            return date(today.year, today.month, day).isoformat()
        except ValueError:
            raise ValueError(
                f"{today.strftime('%B')} does not have day {day}."
            )

    parts = value.split("/")

    # DD/MM
    if len(parts) == 2:
        try:
            day = int(parts[0])
            month = int(parts[1])
            return date(today.year, month, day).isoformat()
        except ValueError:
            raise ValueError(
                "Invalid date format. Try something like 2/9."
            )

    # DD/MM/YYYY
    if len(parts) == 3:
        try:
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])
            return date(year, month, day).isoformat()
        except ValueError:
            raise ValueError(
                "Invalid date format. Try something like 2/9/2026."
            )

    # YYYY-MM-DD
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError(
            "Invalid date. Try 'today', 'yesterday', 2, 2/9, 2/9/2026, or 2026-09-02."
        )


def prompt_date(prompt_text: str = "Date") -> str:
    """Prompt until a valid date is entered."""
    today = date.today()

    while True:
        value = typer.prompt(
            prompt_text,
            default=today.isoformat(),
        )

        try:
            parsed = parse_date(value)
        except ValueError as error:
            typer.echo(f"✗ {error}")
            continue

        parsed_date = date.fromisoformat(parsed)

        if parsed_date > today:
            typer.echo(
                f"⚠ {parsed_date.strftime('%d %B %Y')} is in the future."
            )
            if not typer.confirm("Record this future date?", default=False):
                continue

        return parsed


def prompt_meal(default_meal: str | None = None) -> str:
    """Prompt for lunch or dinner."""
    if default_meal is None:
        default_meal = get_current_meal()

    default_number = 1 if default_meal == "lunch" else 2

    while True:
        value = typer.prompt(
            "Meal [1=Lunch, 2=Dinner]",
            default=str(default_number),
        ).strip().lower()

        if value in ("1", "lunch"):
            return "lunch"
        if value in ("2", "dinner"):
            return "dinner"

        typer.echo("✗ Choose 1 for lunch or 2 for dinner.")


def prompt_type(default_val: str = "1") -> str:
    """Prompt for regular, special, or a custom description."""
    while True:
        value = typer.prompt(
            "  Type [1=Regular, 2=Special, 3=Custom]",
            default=default_val,
        ).strip().lower()

        if value in ("1", "regular"):
            return "Regular"
        if value in ("2", "special"):
            return "Special"
        if value in ("3", "custom"):
            description = typer.prompt("  Description").strip()
            if description:
                return description
            typer.echo("  ✗ Description cannot be empty.")
            continue

        typer.echo("  ✗ Choose 1, 2, or 3.")


def parse_price(value: str) -> int:
    """
    Convert a price string into paise (e.g., 70 -> 7000, 70.50 -> 7050).
    """
    value = (
        value.strip()
        .replace("₹", "")
        .replace(",", "")
        .strip()
    )

    if not value:
        return DEFAULT_PRICE_PAISE

    try:
        amount = Decimal(value)
    except InvalidOperation:
        raise ValueError("Enter a valid price, such as 70 or 70.50.")

    if not amount.is_finite():
        raise ValueError("Price must be a normal number.")

    if amount < 0:
        raise ValueError("Price cannot be negative.")

    if amount.as_tuple().exponent < -2:
        raise ValueError("Price can have at most two decimal places.")

    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(amount * 100)


def prompt_price(default_val: str = "70") -> int:
    """Prompt for a price in Rupees."""
    while True:
        value = typer.prompt("  Price (₹)", default=default_val)
        try:
            return parse_price(value)
        except ValueError as error:
            typer.echo(f"  ✗ {error}")


def prompt_person(people: list[tuple[int, str]]) -> tuple[int, str]:
    """Interactively select a person from the list of people."""
    typer.echo("\nSelect Person:")
    for idx, (person_id, name) in enumerate(people, start=1):
        typer.echo(f"  {idx}. {name}")

    while True:
        value = typer.prompt("Enter person number", default="1").strip()
        if value.isdigit():
            num = int(value)
            if 1 <= num <= len(people):
                return people[num - 1]
        typer.echo(f"✗ Please enter a number between 1 and {len(people)}.")
