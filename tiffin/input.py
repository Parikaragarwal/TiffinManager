from datetime import date, datetime, time
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

    We need at least 3 previous observations before
    trusting the learned behavior.
    """

    if len(history) < 3:
        return False

    ate_count = sum(history)

    return ate_count > len(history) / 2

def parse_date(value: str) -> str:
    """
    Convert friendly date input into YYYY-MM-DD.

    Supported:
        ""              -> today
        today           -> today
        2               -> day 2 of current month/year
        2/9             -> 2 September of current year
        2/9/2026        -> 2 September 2026
        2026-09-02      -> explicit ISO date
    """

    value = value.strip().lower()

    if value == "" or value == "today":
        return date.today().isoformat()

    # Just a day number.
    if value.isdigit():
        day = int(value)
        today = date.today()

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

            return date(
                date.today().year,
                month,
                day,
            ).isoformat()

        except ValueError:
            raise ValueError(
                "Invalid date. Try something like 2/9."
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
                "Invalid date. Try something like 2/9/2026."
            )

    # YYYY-MM-DD
    try:
        return date.fromisoformat(value).isoformat()

    except ValueError:
        raise ValueError(
            "Invalid date. Try 2, 2/9, 2/9/2026, "
            "2026-09-02, or today."
        )


def prompt_date() -> str:
    """Prompt until a valid date is entered."""

    today = date.today()

    while True:
        value = typer.prompt(
            "Date",
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
                f"⚠ {parsed_date.strftime('%d %B %Y')} "
                "is in the future."
            )

            if not typer.confirm(
                "Record this future date?",
                default=False,
            ):
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


def prompt_type() -> str:
    """Prompt for regular, special, or a custom description."""

    while True:
        value = typer.prompt(
            "  Type [1=Regular, 2=Special, 3=Custom]",
            default="1",
        ).strip().lower()

        if value in ("1", "regular"):
            return "Regular"

        if value in ("2", "special"):
            return "Special"

        if value in ("3", "custom"):
            description = typer.prompt(
                "  Description"
            ).strip()

            if description:
                return description

            typer.echo("  ✗ Description cannot be empty.")
            continue

        typer.echo(
            "  ✗ Choose 1, 2, or 3."
        )


def parse_price(value: str) -> int:
    """
    Convert a price into paise.

    Examples:
        70       -> 7000
        70.50    -> 7050
        ₹70      -> 7000
        ₹70.50   -> 7050
    """

    value = (
        value
        .strip()
        .replace("₹", "")
        .replace(",", "")
        .strip()
    )

    if not value:
        return DEFAULT_PRICE_PAISE

    try:
        amount = Decimal(value)

    except InvalidOperation:
        raise ValueError(
            "Enter a valid price, such as 70 or 70.50."
        )

    if not amount.is_finite():
        raise ValueError(
            "Price must be a normal number."
        )

    if amount < 0:
        raise ValueError(
            "Price cannot be negative."
        )

    if amount.as_tuple().exponent < -2:
        raise ValueError(
            "Price can have at most two decimal places."
        )

    amount = amount.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    return int(amount * 100)


def prompt_price() -> int:
    """Prompt for a price, defaulting to ₹70."""

    while True:
        value = typer.prompt(
            "  Price (₹)",
            default="70",
        )

        try:
            return parse_price(value)

        except ValueError as error:
            typer.echo(f"  ✗ {error}")
