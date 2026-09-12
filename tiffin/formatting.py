from datetime import date
import os
import sys

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
    return f"{parsed.strftime('%b')} {parsed.day}"


def display_full_date(value: str) -> str:
    """Convert YYYY-MM-DD into full date."""
    parsed = date.fromisoformat(value)
    return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"


def show_review(
    record_date: str,
    meal: str,
    records: list[dict],
) -> None:
    console.print()

    table = Table(
        title=f"🍱 Review Meal ({meal.capitalize()}) - {display_full_date(record_date)}",
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
        title=f"✓ Recorded: {meal.capitalize()} ({display_full_date(record_date)})",
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
            f"\n[yellow]⚠ No records exist for {display_full_date(record_date)}.[/yellow]"
        )
        return

    console.print()
    console.print(
        Panel(
            f"[bold cyan]🍱 Tiffin Status for {display_full_date(record_date)}[/bold cyan]",
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
    """Display massively detailed report matching the exact 6-section specification."""
    ov = report_data["overview"]
    lvd = report_data["lunch_vs_dinner"]

    console.print()
    console.print(
        Panel(
            f"[bold green]🍱 {period_label} Report[/bold green]",
            border_style="green",
            box=box.ROUNDED,
        )
    )

    # 1. Overview Section
    ov_lines = [
        f"Recorded lunches:       [bold]{ov['recorded_lunches']}[/bold]",
        f"Recorded dinners:      [bold]{ov['recorded_dinners']}[/bold]",
        "",
        f"Total tiffins:         [bold yellow]{ov['total_tiffins']}[/bold yellow]",
        f"Regular:               [bold]{ov['regular']}[/bold]",
        f"Special:               [bold yellow]{ov['special']}[/bold yellow]",
        f"Total cost:          [bold green]{format_rupees(ov['total_cost_paise'])}[/bold green]",
        f"Average / tiffin:    [bold green]{format_rupees(ov['avg_per_tiffin_paise'])}[/bold green]",
    ]
    console.print(Panel("\n".join(ov_lines), title="Overview", border_style="cyan", box=box.ROUNDED))

    # 2. Lunch vs Dinner Section
    lvd_table = Table(title="Lunch vs Dinner Comparison", box=box.ROUNDED, header_style="bold magenta")
    lvd_table.add_column("Metric", style="bold white")
    lvd_table.add_column("Lunch", justify="right", style="cyan")
    lvd_table.add_column("Dinner", justify="right", style="magenta")

    lvd_table.add_row("Tiffins", str(lvd["lunch"]["tiffins"]), str(lvd["dinner"]["tiffins"]))
    lvd_table.add_row("Regular", str(lvd["lunch"]["regular"]), str(lvd["dinner"]["regular"]))
    lvd_table.add_row("Special", str(lvd["lunch"]["special"]), str(lvd["dinner"]["special"]))
    lvd_table.add_row("Cost", format_rupees(lvd["lunch"]["cost_paise"]), format_rupees(lvd["dinner"]["cost_paise"]))

    console.print(lvd_table)

    # 3. People Section
    people_table = Table(title="People Breakdown", box=box.ROUNDED, header_style="bold blue")
    people_table.add_column("Person", style="bold white")
    people_table.add_column("Lunch", justify="center")
    people_table.add_column("Dinner", justify="center")
    people_table.add_column("Total", justify="center", style="yellow")
    people_table.add_column("Special", justify="center", style="bold yellow")
    people_table.add_column("Cost", justify="right", style="bold green")

    for p_id, p_data in report_data["people"].items():
        people_table.add_row(
            p_data["name"],
            str(p_data["lunch"]),
            str(p_data["dinner"]),
            str(p_data["tiffins"]),
            str(p_data["special"]),
            format_rupees(p_data["cost_paise"]),
        )

    console.print(people_table)

    # 4. Daily Breakdown Section
    daily_table = Table(title="Daily Breakdown", box=box.ROUNDED, header_style="bold yellow")
    daily_table.add_column("Date", style="bold white")
    daily_table.add_column("Lunch", justify="center")
    daily_table.add_column("Dinner", justify="center")
    daily_table.add_column("Total", justify="center", style="yellow")
    daily_table.add_column("Cost", justify="right", style="bold green")

    daily_dict = report_data.get("daily", {})
    if daily_dict:
        for d_str, d_data in daily_dict.items():
            l_str = str(d_data["lunch_tiffins"]) if d_data["lunch_recorded"] else "-"
            d_str_val = str(d_data["dinner_tiffins"]) if d_data["dinner_recorded"] else "-"
            daily_table.add_row(
                display_date(d_str),
                l_str,
                d_str_val,
                str(d_data["total_tiffins"]),
                format_rupees(d_data["cost_paise"]),
            )
        console.print(daily_table)

    # 5. Special Tiffins Section
    specials = report_data.get("specials", [])
    if specials:
        specials_table = Table(title="Special Tiffins", box=box.ROUNDED, header_style="bold yellow")
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

    # 6. Unrecorded Section
    unrecorded = report_data.get("unrecorded", [])
    if unrecorded:
        un_table = Table(title="Unrecorded Meals", box=box.ROUNDED, header_style="bold red")
        un_table.add_column("Date", style="bold white")
        un_table.add_column("Meal", style="bold red")

        for item in unrecorded:
            un_table.add_row(
                display_date(item["date"]),
                item["meal"].capitalize(),
            )
        console.print(un_table)


def show_bill(bill_data: dict) -> None:
    """Display overall billing balance or itemized person bill."""
    console.print()

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
                display_full_date(s["settled_date"]),
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
            display_full_date(s["settled_date"]),
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
            display_full_date(item["date"]),
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


def show_history_table(history_data: dict, period_label: str) -> None:
    """Display daily attendance & meal type matrix for each person in a Rich table."""
    people = history_data.get("people", [])
    rows = history_data.get("rows", [])
    person_stats = history_data.get("person_stats", {})

    if not rows:
        console.print(f"\n[yellow]⚠ No history records found for {period_label}.[/yellow]")
        return

    console.print()
    console.print(
        Panel(
            f"[bold cyan]📅 Daily Attendance & Meal History Matrix ({period_label})[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    table = Table(box=box.ROUNDED, header_style="bold magenta")
    table.add_column("Date", style="bold white")
    table.add_column("Meal", style="bold cyan")

    for _, name in people:
        table.add_column(name, justify="center")

    def cell_badge(meal_info):
        if not meal_info:
            return "[dim]—[/dim]"
        if not meal_info["ate"]:
            return "[bold red]✗ Didn't eat[/bold red]"
        desc = (meal_info.get("description") or "Regular").strip()
        if desc.lower() == "special":
            return "[bold yellow]★ Ate (Special)[/bold yellow]"
        return "[bold green]✓ Ate (Regular)[/bold green]"

    for idx, r in enumerate(rows):
        d_str = display_date(r["date"])

        # Lunch row
        lunch_cells = [cell_badge(r["persons"].get(p_id, {}).get("lunch")) for p_id, _ in people]
        table.add_row(d_str, "[cyan]☀️ Lunch[/cyan]", *lunch_cells)

        # Dinner row
        dinner_cells = [cell_badge(r["persons"].get(p_id, {}).get("dinner")) for p_id, _ in people]
        table.add_row("", "[magenta]🌙 Dinner[/magenta]", *dinner_cells, end_section=(idx < len(rows) - 1))

    console.print(table)

    # Summary Panel
    summary_lines = []
    for p_id, s in person_stats.items():
        summary_lines.append(
            f"• [bold]{s['name']:<12}[/bold] Total Ate: [bold green]{s['total_ate']}[/bold green] "
            f"(Lunch: {s['lunch_ate']}, Dinner: {s['dinner_ate']}) | "
            f"Regular: {s['regular_count']}, Special: [bold yellow]{s['special_count']}[/bold yellow] | "
            f"Cost: [green]{format_rupees(s['total_cost_paise'])}[/green]"
        )

    console.print(Panel("\n".join(summary_lines), title="Period Summary", border_style="yellow", box=box.ROUNDED))


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

    cmd_table = Table(
        title="📖 Available Commands",
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    cmd_table.add_column("Command", style="bold yellow")
    cmd_table.add_column("Syntax", style="bold white")
    cmd_table.add_column("Description", style="dim white")

    cmd_table.add_row("record", "tiffin record", "Interactively record lunch/dinner attendance for a date.")
    cmd_table.add_row("today", "tiffin today", "Shortcut to inspect or record today's meal status.")
    cmd_table.add_row("edit", "tiffin edit", "Modify existing recorded entries for any date and meal.")
    cmd_table.add_row("delete", "tiffin delete", "Delete records for a specific date (requires admin/sudo).")
    cmd_table.add_row("status", "tiffin status", "View daily attendance table and cost breakdown.")
    cmd_table.add_row("history", "tiffin history", "Daily attendance & meal type matrix for each person.")
    cmd_table.add_row("settle", "tiffin settle", "Record payment transactions and clear dues.")
    cmd_table.add_row("audit", "tiffin audit", "View chronological settlement payment audit log.")
    cmd_table.add_row("bill", "tiffin bill", "Show overall billing statement or itemized invoice.")
    cmd_table.add_row("report", "tiffin report", "Detailed 6-section analytics consumption report.")
    cmd_table.add_row("missing", "tiffin missing", "Audit missing/unrecorded dates in the current month.")
    cmd_table.add_row("export", "tiffin export", "Export report to CSV, HTML dashboard, or WhatsApp format.")
    cmd_table.add_row("serve", "tiffin serve", "Run live transparent web dashboard server on local network/VPS.")
    cmd_table.add_row("backup", "tiffin backup", "Create automatic local & cloud-synced database backup.")
    cmd_table.add_row("restore", "tiffin restore", "Restore database state from local file or cloud backup.")
    cmd_table.add_row("help", "tiffin help", "Display this user manual.")

    console.print(cmd_table)