import typer

from .reports import get_day_status
from .db import (
    get_ate_history,
    get_people,
    get_recorded_meals,
    initialize_database,
    save_consumption,
    seed_people,
)
from .formatting import (
    console,
    show_review,
    show_saved_summary,
    show_status,
)

from .input import (
    get_learned_ate_default,
    parse_date,
    prompt_date,
    prompt_meal,
    prompt_price,
    prompt_type,
)


app = typer.Typer()


@app.command()
def init():
    """Initialize the Tiffin database."""

    initialize_database()
    seed_people()

    console.print(
        "[green]✓ Tiffin database initialized.[/green]"
    )

@app.command()
def record():
    """Record a meal for everyone."""

    initialize_database()
    seed_people()

    people = get_people()

    console.print("\n[bold]🍱 Tiffin[/bold]\n")

    record_date = prompt_date()
   
    recorded_meals = get_recorded_meals(record_date)
   
    if "lunch" in recorded_meals and "dinner" in recorded_meals:
        console.print(
            "\n[yellow]⚠ Both lunch and dinner are already recorded "
            f"for {record_date}.[/yellow]"
        )
        console.print(
            "[dim]Editing existing entries isn't implemented yet.[/dim]"
        )
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

        console.print(
            f"\n[bold cyan]{name}[/bold cyan]"
        )

        history = get_ate_history(
            person_id,
            meal,
        )
        
        ate_default = get_learned_ate_default(history)
        
        ate = typer.confirm(
            "  Ate?",
            default=ate_default,
        )

        if not ate:
            records.append(
                {
                    "person_id": person_id,
                    "name": name,
                    "ate": False,
                    "description": None,
                    "price_paise": None,
                }
            )

            continue

        description = prompt_type()
        price_paise = prompt_price()

        records.append(
            {
                "person_id": person_id,
                "name": name,
                "ate": True,
                "description": description,
                "price_paise": price_paise,
            }
        )

    show_review(
        record_date,
        meal,
        records,
    )

    console.print()

    if not typer.confirm(
        "Save this?",
        default=True,
    ):
        console.print(
            "\n[yellow]→ Nothing was saved.[/yellow]"
        )
        raise typer.Exit()

    for record in records:
        save_consumption(
            date=record_date,
            meal=meal,
            person_id=record["person_id"],
            ate=record["ate"],
            description=record["description"],
            price_paise=record["price_paise"],
        )

    show_saved_summary(
        record_date,
        meal,
        records,
    )

@app.command()
def status(
    date_value: str = typer.Argument(
        None,
        help="Date to inspect.",
    )
):
    """Show the tiffin status for a date."""

    initialize_database()
    seed_people()

    if date_value is None:
        record_date = prompt_date()
    else:
        try:
            record_date = parse_date(date_value)
        except ValueError as error:
            console.print(f"[red]✗ {error}[/red]")
            raise typer.Exit(code=1)

    day_status = get_day_status(record_date)

    show_status(
        record_date,
        day_status,
    )


if __name__ == "__main__":
    app()
