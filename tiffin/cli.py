from datetime import date
import typer
from rich.console import Console
from rich.panel import Panel
from rich import box

from .db import (
    get_ate_history,
    get_consumption_for_date,
    get_people,
    get_recorded_meals,
    initialize_database,
    save_consumption,
    seed_people,
)
from .settlement_db import (
    get_all_settlements,
    record_settlement,
)
from .billing import (
    get_overall_bill,
    get_person_bill,
)
from .reports import (
    get_day_status,
    get_missing_records,
    get_month_report,
    parse_date_range,
)
from .export import (
    export_bill_to_csv,
    export_month_to_csv,
    generate_whatsapp_summary,
)
from .formatting import (
    console,
    display_date,
    show_audit_log,
    show_bill,
    show_missing_records,
    show_month_report,
    show_review,
    show_saved_summary,
    show_status,
    show_whatsapp_summary,
)
from .input import (
    get_current_meal,
    get_learned_ate_default,
    parse_date,
    parse_price,
    prompt_date,
    prompt_meal,
    prompt_person,
    prompt_price,
    prompt_type,
)

app = typer.Typer(help="🍱 Tiffin - Personal Tiffin & Meal Management CLI")


@app.command()
def init():
    """Initialize the Tiffin database and seed default people."""
    initialize_database()
    seed_people()
    console.print(
        Panel("[bold green]✓ Tiffin database successfully initialized and seeded.[/bold green]", border_style="green", box=box.ROUNDED)
    )


@app.command()
def record():
    """Record a meal for everyone on a given date."""
    initialize_database()
    seed_people()

    people = get_people()
    console.print("\n[bold cyan]🍱 Tiffin Meal Recorder[/bold cyan]\n")

    record_date = prompt_date()
    recorded_meals = get_recorded_meals(record_date)

    if "lunch" in recorded_meals and "dinner" in recorded_meals:
        console.print(
            f"\n[yellow]⚠ Both lunch and dinner are already recorded for {display_date(record_date)}.[/yellow]"
        )
        if typer.confirm("Would you like to edit existing entries instead?", default=True):
            return edit(date_value=record_date)
        raise typer.Exit()

    if "lunch" in recorded_meals:
        default_meal = "dinner"
    elif "dinner" in recorded_meals:
        default_meal = "lunch"
    else:
        default_meal = None

    meal = prompt_meal(default_meal)
    records = []

    for person_id, name in people:
        console.print(f"\n[bold cyan]• {name}[/bold cyan]")
        history = get_ate_history(person_id, meal)
        ate_default = get_learned_ate_default(history)

        ate = typer.confirm("  Ate?", default=ate_default)
        if not ate:
            records.append({
                "person_id": person_id,
                "name": name,
                "ate": False,
                "description": None,
                "price_paise": None,
            })
            continue

        description = prompt_type()
        price_paise = prompt_price()

        records.append({
            "person_id": person_id,
            "name": name,
            "ate": True,
            "description": description,
            "price_paise": price_paise,
        })

    show_review(record_date, meal, records)
    console.print()

    if not typer.confirm("Save this record?", default=True):
        console.print("\n[yellow]→ Action cancelled. Nothing was saved.[/yellow]")
        raise typer.Exit()

    for record_item in records:
        save_consumption(
            date=record_date,
            meal=meal,
            person_id=record_item["person_id"],
            ate=record_item["ate"],
            description=record_item["description"],
            price_paise=record_item["price_paise"],
        )

    show_saved_summary(record_date, meal, records)


@app.command()
def today():
    """Quick shortcut to inspect or record today's meals."""
    initialize_database()
    seed_people()

    today_str = date.today().isoformat()
    recorded_meals = get_recorded_meals(today_str)
    curr_meal = get_current_meal()

    if curr_meal in recorded_meals:
        console.print(f"\n[bold cyan]Today's ({curr_meal.capitalize()}) status:[/bold cyan]")
        day_status = get_day_status(today_str)
        show_status(today_str, day_status)
    else:
        console.print(f"\n[bold green]Recording today's {curr_meal.capitalize()}...[/bold green]")
        record()


@app.command()
def edit(
    date_value: str = typer.Argument(
        None,
        help="Date to edit (e.g., today, yesterday, 2026-09-02, 2/9).",
    )
):
    """Edit existing meal records for a specific date."""
    initialize_database()
    seed_people()

    if date_value is None:
        record_date = prompt_date("Date to edit")
    else:
        try:
            record_date = parse_date(date_value)
        except ValueError as error:
            console.print(f"[red]✗ {error}[/red]")
            raise typer.Exit(code=1)

    meal = prompt_meal()
    existing_rows = get_consumption_for_date(record_date)
    existing_map = {}
    for m, p_id, p_name, ate, desc, price in existing_rows:
        if m == meal:
            existing_map[p_id] = {
                "name": p_name,
                "ate": bool(ate),
                "description": desc,
                "price_paise": price,
            }

    people = get_people()
    console.print(f"\n[bold yellow]✏ Editing {meal.capitalize()} for {display_date(record_date)}[/bold yellow]\n")

    records = []
    for person_id, name in people:
        prev = existing_map.get(person_id)
        prev_ate = prev["ate"] if prev else True
        prev_desc = prev["description"] if prev and prev["description"] else "Regular"
        prev_price = f"{prev['price_paise'] / 100:.2f}" if prev and prev["price_paise"] else "70"

        console.print(f"\n[bold cyan]• {name}[/bold cyan]")
        ate = typer.confirm("  Ate?", default=prev_ate)

        if not ate:
            records.append({
                "person_id": person_id,
                "name": name,
                "ate": False,
                "description": None,
                "price_paise": None,
            })
            continue

        desc_num = "1" if prev_desc.lower() == "regular" else ("2" if prev_desc.lower() == "special" else "3")
        description = prompt_type(desc_num)
        price_paise = prompt_price(prev_price)

        records.append({
            "person_id": person_id,
            "name": name,
            "ate": True,
            "description": description,
            "price_paise": price_paise,
        })

    show_review(record_date, meal, records)
    console.print()

    if not typer.confirm("Update and save changes?", default=True):
        console.print("\n[yellow]→ Changes discarded.[/yellow]")
        raise typer.Exit()

    for record_item in records:
        save_consumption(
            date=record_date,
            meal=meal,
            person_id=record_item["person_id"],
            ate=record_item["ate"],
            description=record_item["description"],
            price_paise=record_item["price_paise"],
        )

    show_saved_summary(record_date, meal, records)


@app.command()
def status(
    date_value: str = typer.Argument(
        None,
        help="Date to inspect (defaults to today).",
    )
):
    """Show tiffin consumption status for a date."""
    initialize_database()
    seed_people()

    if date_value is None:
        record_date = date.today().isoformat()
    else:
        try:
            record_date = parse_date(date_value)
        except ValueError as error:
            console.print(f"[red]✗ {error}[/red]")
            raise typer.Exit(code=1)

    day_status = get_day_status(record_date)
    show_status(record_date, day_status)


@app.command()
def settle():
    """Record a payment/settlement to clear dues for a person."""
    initialize_database()
    seed_people()

    console.print("\n[bold green]💰 Settle Dues / Record Payment[/bold green]")
    show_bill(get_overall_bill())

    people = get_people()
    person_id, name = prompt_person(people)

    console.print(f"\n[bold cyan]Recording settlement for {name}[/bold cyan]")
    price_val = typer.prompt("  Amount Paid (₹)")

    try:
        amount_paise = parse_price(price_val)
    except ValueError as err:
        console.print(f"[red]✗ {err}[/red]")
        raise typer.Exit(code=1)

    settle_date = prompt_date("Settlement Date")
    notes = typer.prompt("Notes (e.g. GPay, Cash, September bill)", default="GPay").strip()

    record_settlement(
        person_id=person_id,
        amount_paise=amount_paise,
        settled_date=settle_date,
        notes=notes,
    )

    console.print(f"\n[bold green]✓ Payment of {price_val} recorded for {name} on {display_date(settle_date)}![/bold green]\n")
    p_bill = get_person_bill(person_id)
    show_bill(p_bill)


@app.command()
def audit():
    """View chronological settlement audit log history."""
    initialize_database()
    seed_people()

    settlements = get_all_settlements()
    show_audit_log(settlements)


@app.command()
def bill(
    person_name: str = typer.Argument(
        None,
        help="Optional person name to view itemized invoice.",
    )
):
    """View billing summary and pending dues balances."""
    initialize_database()
    seed_people()

    if person_name is None:
        overall = get_overall_bill()
        show_bill(overall)
        return

    people = get_people()
    matched = [p for p in people if person_name.lower() in p[1].lower()]
    if not matched:
        console.print(f"[red]✗ No person matching '{person_name}' found.[/red]")
        raise typer.Exit(code=1)

    person_id = matched[0][0]
    p_bill = get_person_bill(person_id)
    show_bill(p_bill)


@app.command()
def report(
    period: str = typer.Option(
        None,
        "--period",
        "-p",
        help="Period or date range (e.g., '2026-09', 'september', or '2026-09-01:2026-09-30').",
    ),
    from_date: str = typer.Option(
        None,
        "--from",
        "-f",
        help="Start date (YYYY-MM-DD).",
    ),
    to_date: str = typer.Option(
        None,
        "--to",
        "-t",
        help="End date (YYYY-MM-DD).",
    ),
):
    """View analytics consumption report between dates or for a month."""
    initialize_database()
    seed_people()

    if from_date and to_date:
        start_date = parse_date(from_date)
        end_date = parse_date(to_date)
        label = f"{display_date(start_date)} to {display_date(end_date)}"
    else:
        start_date, end_date, label = parse_date_range(period)

    month_data = get_month_report(start_date, end_date)
    show_month_report(month_data, label)


@app.command()
def missing():
    """Audit unrecorded/missing meal dates for the current month."""
    initialize_database()
    seed_people()

    missing_list = get_missing_records()
    show_missing_records(missing_list)


@app.command()
def export(
    output_type: str = typer.Option(
        "csv",
        "--type",
        "-t",
        help="Export format: 'csv' or 'whatsapp'.",
    ),
    filename: str = typer.Option(
        "tiffin_bill.csv",
        "--out",
        "-o",
        help="Output CSV filename.",
    ),
):
    """Export billing / report to CSV or display WhatsApp text format."""
    initialize_database()
    seed_people()

    if output_type.lower() == "whatsapp":
        text = generate_whatsapp_summary()
        show_whatsapp_summary(text)
        return

    path = export_bill_to_csv(filename)
    console.print(
        Panel(
            f"[bold green]✓ Exported billing statement to CSV:[/bold green]\n[cyan]{path.resolve()}[/cyan]",
            border_style="green",
            box=box.ROUNDED,
        )
    )


if __name__ == "__main__":
    app()
