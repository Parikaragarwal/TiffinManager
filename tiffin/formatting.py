from datetime import date

from rich.console import Console
from rich.table import Table


console = Console()

def format_rupees(paise: int | None) -> str:
    """Convert paise into a displayable rupee amount."""

    if paise is None:
        return "—"

    return f"₹{paise / 100:.2f}"


def display_date(value: str) -> str:
    """Convert YYYY-MM-DD into a human-friendly date."""

    parsed = date.fromisoformat(value)

    return parsed.strftime("%B %-d, %Y")


def show_review(
    record_date: str,
    meal: str,
    records: list[dict],
) -> None:

    console.print()

    table = Table(
        title="🍱 Review",
    )

    table.add_column("Person", style="bold")
    table.add_column("Status")
    table.add_column("Type")
    table.add_column("Price", justify="right")

    total_paise = 0
    people_ate = 0

    for record in records:

        if record["ate"]:
            status = "[green]✓ Ate[/green]"
            description = record["description"]
            price = format_rupees(record["price_paise"])

            total_paise += record["price_paise"]
            people_ate += 1

        else:
            status = "[dim]✗ Didn't eat[/dim]"
            description = "—"
            price = "—"

        table.add_row(
            record["name"],
            status,
            description,
            price,
        )

    console.print(
        f"[bold]Date:[/bold] {display_date(record_date)}"
    )

    console.print(
        f"[bold]Meal:[/bold] {meal.capitalize()}\n"
    )

    console.print(table)

    console.print(
        f"\n[bold]People ate:[/bold] {people_ate}"
    )

    console.print(
        f"\n[bold]Total:[/bold] {format_rupees(total_paise)}"
    )


def show_saved_summary(
    record_date: str,
    meal: str,
    records: list[dict],
) -> None:

    total_paise = 0
    people_ate = 0
    special_count = 0

    table = Table(
        title="✓ Recorded",
    )

    table.add_column("Person", style="bold")
    table.add_column("Status")
    table.add_column("Type")
    table.add_column("Price", justify="right")

    for record in records:

        if record["ate"]:
            people_ate += 1
            total_paise += record["price_paise"]

            description = record["description"]

            if description.strip().lower() == "special":
                special_count += 1

            table.add_row(
                record["name"],
                "[green]✓[/green]",
                description,
                format_rupees(record["price_paise"]),
            )

        else:
            table.add_row(
                record["name"],
                "[red]✗[/red]",
                "—",
                "—",
            )

    console.print()

    console.print(
        f"[bold green]✓ {meal.capitalize()} recorded![/bold green]"
    )

    console.print(
        f"[bold]{display_date(record_date)}[/bold]\n"
    )

    console.print(table)

    console.print()

    console.print(
        f"[bold]Tiffins:[/bold] {people_ate}"
    )

    console.print(
        f"[bold]Special:[/bold] {special_count}"
    )

    console.print(
        f"[bold]Total:[/bold] {format_rupees(total_paise)}"
    )

    
def show_status(record_date: str, status: dict) -> None:
        """Display the status and analysis for one day."""
    
        if not status["lunch"] and not status["dinner"]:
            console.print(
                f"\n[yellow]No record for {display_date(record_date)} "
                "exists.[/yellow]"
            )
            return
    
        console.print()
        console.print("[bold]🍱 Tiffin Status[/bold]")
        console.print(f"[bold]{display_date(record_date)}[/bold]\n")
    
        table = Table()
    
        table.add_column("Person", style="bold")
        table.add_column("Lunch")
        table.add_column("Dinner")
    
        people = {}
    
        for meal in ("lunch", "dinner"):
            for person_id, record in status[meal].items():
                people[person_id] = record["name"]
    
        total_tiffins = 0
        total_paise = 0
    
        person_stats = {
            person_id: {
                "name": name,
                "tiffins": 0,
                "price_paise": 0,
            }
            for person_id, name in people.items()
        }
    
        def cell(record):
            if record is None:
                return "[dim]?[/dim]"
    
            if not record["ate"]:
                return "[red]✗[/red]"
    
            description = record["description"]
            price = format_rupees(record["price_paise"])
    
            return (
                f"[green]✓[/green] "
                f"{description} {price}"
            )
    
        for person_id, name in people.items():
    
            lunch = status["lunch"].get(person_id)
            dinner = status["dinner"].get(person_id)
    
            for record in (lunch, dinner):
                if record and record["ate"]:
                    total_tiffins += 1
                    total_paise += record["price_paise"]
    
                    person_stats[person_id]["tiffins"] += 1
                    person_stats[person_id]["price_paise"] += (
                        record["price_paise"]
                    )
    
            table.add_row(
                name,
                cell(lunch),
                cell(dinner),
            )
    
        console.print(table)
    
        console.print("\n[bold]Summary[/bold]")
    
        for person in person_stats.values():
            console.print(
                f"{person['name']:<12} "
                f"{person['tiffins']} tiffin(s)   "
                f"{format_rupees(person['price_paise'])}"
            )
    
        console.print(
            f"\n[bold]Total tiffins:[/bold] {total_tiffins}"
        )
    
        console.print(
            f"[bold]Total cost:[/bold] "
            f"{format_rupees(total_paise)}"
        )
    
        console.print("\n[bold]Analysis[/bold]")
    
        lunch_recorded = bool(status["lunch"])
        dinner_recorded = bool(status["dinner"])
    
        if lunch_recorded:
            console.print("• Lunch is recorded.")
        else:
            console.print("• Lunch is not recorded.")
    
        if dinner_recorded:
            console.print("• Dinner is recorded.")
        else:
            console.print("• Dinner is not recorded.")
    
        if total_tiffins:
            console.print(
                f"• {total_tiffins} tiffin(s) were consumed."
            )
    
        if total_paise:
            console.print(
                f"• Total cost was {format_rupees(total_paise)}."
            )