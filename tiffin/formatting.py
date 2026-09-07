from datetime import date
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


def format_rupees(paise: int | None) -> str:
    """Convert paise into a displayable rupee amount."""
    if paise is None:
        return "—"
    return f"₹{paise / 100:.2f}"


def display_date(value: str) -> str:
    """Convert YYYY-MM-DD into a human-friendly date."""
    parsed = date.fromisoformat(value)
    return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"


def show_review(
    record_date: str,
    meal: str,
    records: list[dict],
) -> None:
    console.print()

    table = Table(
        title=f"🍱 Review Meal ({meal.capitalize()}) - {display_date(record_date)}",
        box=box.ROUNDED,
        header_style="bold cyan",
    )

    table.add_column("Person", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Type")
    table.add_column("Price", justify="right", style="bold green")

    total_paise = 0
    people_ate = 0

    for record in records:
        if record["ate"]:
            status = "[bold green]✓ Ate[/bold green]"
            description = record["description"] or "Regular"
            price = format_rupees(record["price_paise"])
            total_paise += record["price_paise"] or 0
            people_ate += 1
        else:
            status = "[dim red]✗ Didn't eat[/dim red]"
            description = "—"
            price = "—"

        table.add_row(
            record["name"],
            status,
            description,
            price,
        )

    console.print(table)

    summary_text = (
        f"[bold]People Ate:[/bold] [cyan]{people_ate}/{len(records)}[/cyan]   |   "
        f"[bold]Total Cost:[/bold] [bold green]{format_rupees(total_paise)}[/bold green]"
    )
    console.print(Panel(summary_text, title="Review Summary", border_style="cyan", box=box.ROUNDED))


def show_saved_summary(
    record_date: str,
    meal: str,
    records: list[dict],
) -> None:
    total_paise = 0
    people_ate = 0
    special_count = 0

    table = Table(
        title=f"✓ Recorded: {meal.capitalize()} ({display_date(record_date)})",
        box=box.ROUNDED,
        header_style="bold green",
    )

    table.add_column("Person", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Type")
    table.add_column("Price", justify="right", style="green")

    for record in records:
        if record["ate"]:
            people_ate += 1
            total_paise += record["price_paise"] or 0
            description = record["description"] or "Regular"

            if description.strip().lower() == "special":
                special_count += 1
                type_display = "[bold yellow]★ Special[/bold yellow]"
            else:
                type_display = description

            table.add_row(
                record["name"],
                "[bold green]✓[/bold green]",
                type_display,
                format_rupees(record["price_paise"]),
            )
        else:
            table.add_row(
                record["name"],
                "[bold red]✗[/bold red]",
                "—",
                "—",
            )

    console.print()
    console.print(table)

    info_panel = (
        f"[bold green]✓ Record saved successfully![/bold green]\n\n"
        f"• [bold]Tiffins Consumed:[/bold] {people_ate}\n"
        f"• [bold]Special Meals:[/bold] {special_count}\n"
        f"• [bold]Total Amount:[/bold] [bold green]{format_rupees(total_paise)}[/bold green]"
    )
    console.print(Panel(info_panel, title="Saved Record Details", border_style="green", box=box.ROUNDED))


def show_status(record_date: str, status: dict) -> None:
    """Display the status and analysis for one day."""
    if not status["lunch"] and not status["dinner"]:
        console.print(
            f"\n[yellow]⚠ No records exist for {display_date(record_date)}.[/yellow]"
        )
        return

    console.print()
    console.print(
        Panel(
            f"[bold cyan]🍱 Tiffin Status for {display_date(record_date)}[/bold cyan]",
            box=box.ROUNDED,
            border_style="cyan",
        )
    )

    table = Table(box=box.ROUNDED, header_style="bold magenta")
    table.add_column("Person", style="bold white")
    table.add_column("Lunch", justify="center")
    table.add_column("Dinner", justify="center")

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
            return "[dim font_style=italic]Not Recorded[/dim font_style=italic]"
        if not record["ate"]:
            return "[bold red]✗ Didn't Eat[/bold red]"

        description = record["description"] or "Regular"
        price = format_rupees(record["price_paise"])
        return f"[bold green]✓ Ate[/bold green] ({description}) [green]{price}[/green]"

    for person_id, name in people.items():
        lunch = status["lunch"].get(person_id)
        dinner = status["dinner"].get(person_id)

        for record in (lunch, dinner):
            if record and record["ate"]:
                total_tiffins += 1
                total_paise += record["price_paise"] or 0
                person_stats[person_id]["tiffins"] += 1
                person_stats[person_id]["price_paise"] += record["price_paise"] or 0

        table.add_row(
            name,
            cell(lunch),
            cell(dinner),
        )

    console.print(table)

    summary_lines = []
    for person in person_stats.values():
        summary_lines.append(
            f"• [bold]{person['name']:<12}[/bold] {person['tiffins']} tiffin(s) — [green]{format_rupees(person['price_paise'])}[/green]"
        )
    summary_lines.append(
        f"\n[bold yellow]Total Tiffins:[/bold yellow] {total_tiffins}   |   [bold yellow]Total Cost:[/bold yellow] [bold green]{format_rupees(total_paise)}[/bold green]"
    )

    console.print(Panel("\n".join(summary_lines), title="Day Summary", border_style="yellow", box=box.ROUNDED))


def show_month_report(report_data: dict, period_label: str) -> None:
    """Display comprehensive report for a month or date range."""
    overview = report_data["overview"]

    console.print()
    header_panel = (
        f"[bold cyan]📊 Tiffin Analytics & Consumption Report[/bold cyan]\n"
        f"[dim]Scope: {period_label}[/dim]\n\n"
        f"• Total Tiffins Consumed: [bold yellow]{overview['tiffins']}[/bold yellow] "
        f"(Regular: {overview['regular']}, Special: {overview['special']})\n"
        f"• Total Consumption Charges: [bold green]{format_rupees(overview['cost_paise'])}[/bold green]"
    )
    console.print(Panel(header_panel, border_style="cyan", box=box.ROUNDED))

    # People Breakdown Table
    people_table = Table(
        title="👥 Breakdown by Person",
        box=box.ROUNDED,
        header_style="bold blue",
    )
    people_table.add_column("Person", style="bold white")
    people_table.add_column("Total Tiffins", justify="center", style="yellow")
    people_table.add_column("Lunch", justify="center")
    people_table.add_column("Dinner", justify="center")
    people_table.add_column("Regular", justify="center")
    people_table.add_column("Special", justify="center")
    people_table.add_column("Total Cost", justify="right", style="bold green")

    for p_id, p_data in report_data["people"].items():
        people_table.add_row(
            p_data["name"],
            str(p_data["tiffins"]),
            str(p_data["lunch"]),
            str(p_data["dinner"]),
            str(p_data["regular"]),
            str(p_data["special"]),
            format_rupees(p_data["cost_paise"]),
        )

    console.print(people_table)

    # Meals Breakdown Table
    meals_table = Table(
        title="🍱 Meal Type Summary",
        box=box.ROUNDED,
        header_style="bold magenta",
    )
    meals_table.add_column("Meal", style="bold magenta")
    meals_table.add_column("Sessions Recorded", justify="center")
    meals_table.add_column("Tiffins Consumed", justify="center", style="yellow")
    meals_table.add_column("Total Cost", justify="right", style="bold green")

    for meal_name, m_data in report_data["meals"].items():
        meals_table.add_row(
            meal_name.capitalize(),
            str(m_data["recorded"]),
            str(m_data["tiffins"]),
            format_rupees(m_data["cost_paise"]),
        )

    console.print(meals_table)

    # Special Items Table if any
    specials = report_data.get("specials", [])
    if specials:
        specials_table = Table(
            title="★ Special Meals List",
            box=box.ROUNDED,
            header_style="bold yellow",
        )
        specials_table.add_column("Date", style="dim")
        specials_table.add_column("Meal", style="bold cyan")
        specials_table.add_column("Person", style="bold white")
        specials_table.add_column("Price", justify="right", style="bold green")

        for s in specials:
            specials_table.add_row(
                display_date(s["date"]),
                s["meal"].capitalize(),
                s["name"],
                format_rupees(s["price_paise"]),
            )

        console.print(specials_table)


def show_bill(bill_data: dict) -> None:
    """Display overall billing balance or itemized person bill."""
    console.print()

    # If overall summary bill
    if "balances" in bill_data:
        console.print(
            Panel(
                "[bold green]💰 Overall Tiffin Billing & Dues Statement[/bold green]",
                box=box.ROUNDED,
                border_style="green",
            )
        )

        table = Table(box=box.ROUNDED, header_style="bold cyan")
        table.add_column("Person", style="bold white")
        table.add_column("Tiffins Eaten", justify="center", style="yellow")
        table.add_column("Total Bill", justify="right", style="bold white")
        table.add_column("Amount Paid", justify="right", style="bold green")
        table.add_column("Pending Dues", justify="right")

        for b in bill_data["balances"]:
            pending = b["pending_paise"]
            if pending > 0:
                pending_str = f"[bold red]{format_rupees(pending)}[/bold red]"
            elif pending < 0:
                pending_str = f"[bold green]{format_rupees(-pending)} Surplus[/bold green]"
            else:
                pending_str = "[dim green]✓ Cleared[/dim green]"

            table.add_row(
                b["name"],
                str(b["tiffins"]),
                format_rupees(b["total_cost_paise"]),
                format_rupees(b["total_settled_paise"]),
                pending_str,
            )

        console.print(table)

        tot_pending = bill_data["total_pending_paise"]
        if tot_pending > 0:
            tot_pending_str = f"[bold red]{format_rupees(tot_pending)}[/bold red]"
        else:
            tot_pending_str = f"[bold green]{format_rupees(tot_pending)}[/bold green]"

        summary_box = (
            f"[bold]Total Tiffins:[/bold] {bill_data['total_tiffins']}   |   "
            f"[bold]Total Bill:[/bold] {format_rupees(bill_data['total_cost_paise'])}   |   "
            f"[bold]Total Paid:[/bold] [green]{format_rupees(bill_data['total_settled_paise'])}[/green]   |   "
            f"[bold]Net Dues:[/bold] {tot_pending_str}"
        )
        console.print(Panel(summary_box, title="Total Balance Summary", border_style="yellow", box=box.ROUNDED))
        return

    # Itemized single person bill
    name = bill_data["name"]
    console.print(
        Panel(
            f"[bold cyan]🧾 Detailed Tiffin Invoice — {name}[/bold cyan]",
            box=box.ROUNDED,
            border_style="cyan",
        )
    )

    table = Table(title=f"Consumption History ({bill_data['tiffins_count']} Tiffins)", box=box.ROUNDED, header_style="bold blue")
    table.add_column("Date", style="dim")
    table.add_column("Meal", style="bold cyan")
    table.add_column("Description")
    table.add_column("Price", justify="right", style="bold green")

    for item in bill_data["meals_detail"]:
        table.add_row(
            display_date(item["date"]),
            item["meal"].capitalize(),
            item["description"],
            format_rupees(item["price_paise"]),
        )

    console.print(table)

    if bill_data["settlements"]:
        settle_table = Table(title="Payment / Settlement History", box=box.ROUNDED, header_style="bold green")
        settle_table.add_column("Date", style="dim")
        settle_table.add_column("Amount", justify="right", style="bold green")
        settle_table.add_column("Notes", style="italic")

        for s in bill_data["settlements"]:
            settle_table.add_row(
                display_date(s["settled_date"]),
                format_rupees(s["amount_paise"]),
                s["notes"] or "—",
            )
        console.print(settle_table)

    pending = bill_data["pending_paise"]
    if pending > 0:
        p_status = f"[bold red]Pending Dues: {format_rupees(pending)}[/bold red]"
    elif pending < 0:
        p_status = f"[bold green]Surplus Credit: {format_rupees(-pending)}[/bold green]"
    else:
        p_status = "[bold green]✓ All Dues Cleared![/bold green]"

    console.print(
        Panel(
            f"• Total Charges: {format_rupees(bill_data['total_cost_paise'])}\n"
            f"• Total Paid: {format_rupees(bill_data['total_settled_paise'])}\n\n"
            f"{p_status}",
            title="Account Summary",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )


def show_audit_log(settlements: list[dict]) -> None:
    """Display settlement payment history log."""
    if not settlements:
        console.print("\n[yellow]⚠ No settlements recorded yet.[/yellow]")
        return

    console.print()
    table = Table(
        title="📜 Settlement Payment Audit Log",
        box=box.ROUNDED,
        header_style="bold green",
    )
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Date", style="bold white")
    table.add_column("Person", style="bold cyan")
    table.add_column("Amount Settled", justify="right", style="bold green")
    table.add_column("Notes", style="italic")

    total_settled = 0
    for s in settlements:
        total_settled += s["amount_paise"]
        table.add_row(
            str(s["id"]),
            display_date(s["settled_date"]),
            s["person_name"],
            format_rupees(s["amount_paise"]),
            s["notes"] or "—",
        )

    console.print(table)
    console.print(
        Panel(
            f"[bold]Total Settled Amount across all entries:[/bold] [bold green]{format_rupees(total_settled)}[/bold green]",
            border_style="green",
            box=box.ROUNDED,
        )
    )


def show_missing_records(missing_list: list[dict]) -> None:
    """Display unrecorded days / missing meals."""
    if not missing_list:
        console.print("\n[bold green]✓ All days in this month have complete lunch and dinner records![/bold green]")
        return

    console.print()
    table = Table(
        title="⚠ Unrecorded / Missing Meals Audit",
        box=box.ROUNDED,
        header_style="bold yellow",
    )
    table.add_column("Date", style="bold white")
    table.add_column("Missing Meal(s)", style="bold red")

    for item in missing_list:
        meals_str = ", ".join(m.capitalize() for m in item["missing_meals"])
        table.add_row(
            display_date(item["date"]),
            meals_str,
        )

    console.print(table)
    console.print(
        Panel(
            f"[yellow]Found [bold]{len(missing_list)}[/bold] date(s) with missing meal entries.[/yellow]\n"
            "Use [bold]python -m tiffin record[/bold] or [bold]python -m tiffin edit[/bold] to complete them.",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )


def show_whatsapp_summary(summary_text: str) -> None:
    """Display WhatsApp text summary in a box for easy copying."""
    console.print()
    console.print(
        Panel(
            Text(summary_text, style="green"),
            title="📲 Copy-paste for WhatsApp / Messages",
            border_style="green",
            box=box.ROUNDED,
        )
    )


def show_help_manual() -> None:
    """Display a rich, simple-to-understand CLI Man Page & User Reference Manual."""
    console.print()
    title_banner = Panel(
        "[bold green]🍱 TIFFIN CLI — USER MANUAL & REFERENCE GUIDE[/bold green]\n"
        "[dim]Simple, elegant, and powerful personal tiffin tracking[/dim]",
        border_style="green",
        box=box.ROUNDED,
    )
    console.print(title_banner)

    # Command Table
    cmd_table = Table(
        title="📖 Available Commands",
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    cmd_table.add_column("Command", style="bold yellow")
    cmd_table.add_column("Syntax", style="bold white")
    cmd_table.add_column("Description", style="dim white")

    cmd_table.add_row(
        "record",
        "tiffin record",
        "Interactively record lunch/dinner attendance and prices for everyone on a given date.",
    )
    cmd_table.add_row(
        "today",
        "tiffin today",
        "Quick shortcut to inspect today's meal status or record current meal if unrecorded.",
    )
    cmd_table.add_row(
        "edit",
        "tiffin edit [date]",
        "Modify or fix existing recorded entries for any date and meal.",
    )
    cmd_table.add_row(
        "status",
        "tiffin status [date]",
        "View daily attendance table and cost breakdown for a date.",
    )
    cmd_table.add_row(
        "settle",
        "tiffin settle",
        "Record payment transactions and clear dues for any person.",
    )
    cmd_table.add_row(
        "audit",
        "tiffin audit",
        "View chronological settlement payment audit trail.",
    )
    cmd_table.add_row(
        "bill",
        "tiffin bill [name]",
        "Show overall financial balance statement or individual itemized invoice.",
    )
    cmd_table.add_row(
        "report",
        "tiffin report [--scope unsettled|month|all]",
        "Analytics consumption report. Defaults to unsettled dues period.",
    )
    cmd_table.add_row(
        "missing",
        "tiffin missing",
        "Audit missing/unrecorded dates in the current month.",
    )
    cmd_table.add_row(
        "export",
        "tiffin export [--type csv|whatsapp]",
        "Export billing & consumption report to CSV or WhatsApp text format.",
    )
    cmd_table.add_row(
        "help",
        "tiffin help",
        "Display this comprehensive user manual & reference guide.",
    )

    console.print(cmd_table)

    # Shortcut Hints Panel
    hints_text = (
        "[bold cyan]💡 Format Guidance & Input Directions:[/bold cyan]\n\n"
        "• [bold yellow]Dates:[/bold yellow] Accepts [bold]today[/bold], [bold]yesterday[/bold], day number e.g. [bold]2[/bold], [bold]2/9[/bold] (2nd Sep), or ISO [bold]2026-09-02[/bold].\n"
        "• [bold yellow]Prices:[/bold yellow] Accepts [bold]70[/bold] (₹70), [bold]70.50[/bold] (₹70.50), or [bold]₹70[/bold]. Defaults to ₹70.\n"
        "• [bold yellow]Meals:[/bold yellow] Type [bold]1[/bold] for Lunch, [bold]2[/bold] for Dinner.\n"
        "• [bold yellow]Types:[/bold yellow] Type [bold]1[/bold] for Regular (₹70), [bold]2[/bold] for Special, [bold]3[/bold] for Custom text.\n"
        "• [bold yellow]Report Scopes:[/bold yellow]\n"
        "   - [bold]unsettled[/bold] (default): From earliest un-cleared consumption to today.\n"
        "   - [bold]month[/bold]: 1st of current month to end of current month.\n"
        "   - [bold]all[/bold]: Entire history in the database."
    )

    console.print(Panel(hints_text, title="Keyboard Shortcuts & Hints", border_style="cyan", box=box.ROUNDED))