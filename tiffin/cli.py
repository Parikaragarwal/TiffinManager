import os
import sys
from datetime import date
import typer
from rich.console import Console
from rich.panel import Panel
from rich import box

from .db import (
    delete_consumption_record,
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
    get_daily_history_matrix,
    get_missing_records,
    get_month_report,
    parse_date_range,
)
from .export import (
    export_bill_to_csv,
    export_history_to_csv,
    export_history_to_html,
    generate_whatsapp_summary,
)
from .formatting import (
    console,
    display_full_date,
    show_audit_log,
    show_bill,
    show_help_manual,
    show_history_table,
    show_missing_records,
    show_month_report,
    show_review,
    show_saved_summary,
    show_status,
    show_whatsapp_summary,
)
from .backup import create_db_backup, export_db_to_json, restore_db_from_file
from .server import run_server, generate_systemd_service, generate_nginx_config
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


def check_sudo_permission():
    """Verify admin / root privileges or prompt confirmation for administrative operations."""
    if os.name == 'posix' and os.geteuid() == 0:
        return True
    
    console.print("\n[bold red]🔒 Administrative Privileges Required[/bold red]")
    console.print("[dim]Deleting records modifies core database consumption logs.[/dim]")
    confirm = typer.prompt("Enter admin confirmation password to proceed (or 'sudo' code)", hide_input=True)
    if confirm.strip().lower() not in ("sudo", "admin", "yes", "confirm", "1234"):
        console.print("[red]✗ Access denied. Incorrect confirmation password.[/red]")
        raise typer.Exit(code=1)
    return True


@app.command(name="help")
def help_cmd():
    """Display the beautiful interactive user manual & reference guide."""
    show_help_manual()


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
    """Record a meal for everyone on a given date with smart defaults."""
    initialize_database()
    seed_people()

    people = get_people()
    console.print("\n[bold cyan]🍱 Tiffin Meal Recorder[/bold cyan]\n")

    record_date = prompt_date("Select Date to Record", default_val=date.today().isoformat())
    recorded_meals = get_recorded_meals(record_date)

    if "lunch" in recorded_meals and "dinner" in recorded_meals:
        console.print(
            f"\n[yellow]⚠ Both lunch and dinner are already recorded for {display_full_date(record_date)}.[/yellow]"
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
    """Edit existing meal records for a specific date (prompts interactively if empty)."""
    initialize_database()
    seed_people()

    if date_value is None:
        record_date = prompt_date("Select Date to Edit", default_val=date.today().isoformat())
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
    console.print(f"\n[bold yellow]✏ Editing {meal.capitalize()} for {display_full_date(record_date)}[/bold yellow]\n")

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
def delete(
    date_value: str = typer.Argument(
        None,
        help="Date to delete (e.g., today, yesterday, 2026-09-02).",
    )
):
    """Delete consumption records for a specific date (requires admin/sudo verification)."""
    initialize_database()
    seed_people()

    check_sudo_permission()

    if date_value is None:
        record_date = prompt_date("Select Date to Delete", default_val=date.today().isoformat())
    else:
        try:
            record_date = parse_date(date_value)
        except ValueError as error:
            console.print(f"[red]✗ {error}[/red]")
            raise typer.Exit(code=1)

    typer.echo("\nMeal Deletion Option:")
    typer.echo("  1. Delete Lunch only")
    typer.echo("  2. Delete Dinner only")
    typer.echo("  3. Delete Both Lunch and Dinner")

    opt = typer.prompt("Select option [1-3]", default="3").strip()
    if opt == "1":
        target_meal = "lunch"
    elif opt == "2":
        target_meal = "dinner"
    else:
        target_meal = None

    meal_label = target_meal.capitalize() if target_meal else "Both Lunch & Dinner"
    console.print(
        f"\n[bold red]⚠️ WARNING: You are about to permanently delete {meal_label} for {display_full_date(record_date)}.[/bold red]"
    )

    if not typer.confirm("Are you sure you want to delete these records?", default=False):
        console.print("[yellow]→ Deletion cancelled.[/yellow]")
        raise typer.Exit()

    count = delete_consumption_record(record_date, target_meal)
    console.print(
        Panel(
            f"[bold green]✓ Successfully deleted {count} consumption record(s) for {display_full_date(record_date)}.[/bold green]",
            border_style="green",
            box=box.ROUNDED,
        )
    )


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
    price_val = typer.prompt("  Amount Paid in Rupees (₹) [e.g. 500 or 770]")

    try:
        amount_paise = parse_price(price_val)
    except ValueError as err:
        console.print(f"[red]✗ {err}[/red]")
        raise typer.Exit(code=1)

    settle_date = prompt_date("Settlement Date", default_val=date.today().isoformat())
    notes = typer.prompt("  Notes/Payment Method (e.g. GPay, Cash, September bill)", default="GPay").strip()

    record_settlement(
        person_id=person_id,
        amount_paise=amount_paise,
        settled_date=settle_date,
        notes=notes,
    )

    console.print(f"\n[bold green]✓ Payment of {price_val} recorded for {name} on {display_full_date(settle_date)}![/bold green]\n")
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
    scope: str = typer.Option(
        "month",
        "--scope",
        "-s",
        help="Report scope if no period specified: 'month' (default: current month), 'unsettled' (un-cleared dues), or 'all' (entire history).",
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
    """View massively detailed 6-section analytics consumption report."""
    initialize_database()
    seed_people()

    if from_date and to_date:
        start_date = parse_date(from_date)
        end_date = parse_date(to_date)
        label = f"{display_full_date(start_date)} to {display_full_date(end_date)}"
    else:
        start_date, end_date, label = parse_date_range(period, scope=scope.lower())

    month_data = get_month_report(start_date, end_date)
    show_month_report(month_data, label)


@app.command()
def history(
    period: str = typer.Option(
        None,
        "--period",
        "-p",
        help="Period or date range (e.g., '2026-09', 'september', or '2026-09-01:2026-09-30').",
    ),
    scope: str = typer.Option(
        "month",
        "--scope",
        "-s",
        help="Report scope if no period specified: 'month' (default: current month), 'unsettled', or 'all'.",
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
    person: str = typer.Option(
        None,
        "--person",
        "-u",
        help="Filter attendance history for a specific person.",
    ),
    out: str = typer.Option(
        None,
        "--out",
        "-o",
        help="Directly export daily attendance table to CSV filename.",
    ),
):
    """View daily attendance table with day/night status and meal types (regular vs special) for each person."""
    initialize_database()
    seed_people()

    if from_date and to_date:
        start_date = parse_date(from_date)
        end_date = parse_date(to_date)
        label = f"{display_full_date(start_date)} to {display_full_date(end_date)}"
    else:
        start_date, end_date, label = parse_date_range(period, scope=scope.lower())

    history_data = get_daily_history_matrix(start_date, end_date, person_filter=person)

    if out:
        path = export_history_to_csv(history_data, out)
        console.print(
            Panel(
                f"[bold green]✓ Exported daily attendance history to CSV:[/bold green]\n[cyan]{path.resolve()}[/cyan]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
        return

    show_history_table(history_data, label)


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
        help="Export format: 'csv' (bill), 'history' (CSV matrix), 'html' (Web dashboard), or 'whatsapp'.",
    ),
    filename: str = typer.Option(
        None,
        "--out",
        "-o",
        help="Output filename.",
    ),
):
    """Export billing / report to CSV, HTML web dashboard, or display WhatsApp text format."""
    initialize_database()
    seed_people()

    t_type = output_type.lower()
    if t_type == "whatsapp":
        text = generate_whatsapp_summary()
        show_whatsapp_summary(text)
        return

    if t_type in ("history", "matrix"):
        out_name = filename or "tiffin_history.csv"
        start_date, end_date, _ = parse_date_range(scope="month")
        history_data = get_daily_history_matrix(start_date, end_date)
        path = export_history_to_csv(history_data, out_name)
        console.print(
            Panel(
                f"[bold green]✓ Exported daily history matrix to CSV:[/bold green]\n[cyan]{path.resolve()}[/cyan]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
        return

    if t_type == "html":
        out_name = filename or "tiffin_history.html"
        start_date, end_date, _ = parse_date_range(scope="month")
        history_data = get_daily_history_matrix(start_date, end_date)
        path = export_history_to_html(history_data, out_name)
        console.print(
            Panel(
                f"[bold green]✓ Exported interactive HTML Web Dashboard:[/bold green]\n[cyan]{path.resolve()}[/cyan]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
        return

    out_name = filename or "tiffin_bill.csv"
    path = export_bill_to_csv(out_name)
    console.print(
        Panel(
            f"[bold green]✓ Exported billing statement to CSV:[/bold green]\n[cyan]{path.resolve()}[/cyan]",
            border_style="green",
            box=box.ROUNDED,
        )
    )


@app.command()
def serve(
    port: int = typer.Option(
        8765,
        "--port",
        "-p",
        help="Port to run the live dashboard server on (default: 8765).",
    ),
    bg: bool = typer.Option(
        False,
        "--bg",
        "-b",
        help="Run live web server in the background.",
    ),
    systemd: bool = typer.Option(
        False,
        "--systemd",
        help="Generate systemd service file for VPS hosting.",
    ),
    nginx: bool = typer.Option(
        False,
        "--nginx",
        help="Generate Nginx reverse proxy configuration for custom domain.",
    ),
    domain: str = typer.Option(
        "tiffin.parikar.in",
        "--domain",
        "-d",
        help="Domain name for Nginx configuration.",
    ),
):
    """Run live transparent web dashboard server for flatmates/friends."""
    initialize_database()
    seed_people()

    if systemd:
        content = generate_systemd_service(port=port)
        console.print("\n[bold cyan]📋 Systemd Service Configuration (for VPS hosting):[/bold cyan]\n")
        console.print(Panel(content, title="tiffin-server.service", border_style="cyan", box=box.ROUNDED))
        console.print("\n[dim]Save this content to /etc/systemd/system/tiffin-server.service on your VPS.[/dim]")
        return

    if nginx:
        content = generate_nginx_config(domain=domain, port=port)
        console.print(f"\n[bold cyan]🌐 Nginx Reverse Proxy Config for {domain}:[/bold cyan]\n")
        console.print(Panel(content, title=f"/etc/nginx/sites-available/{domain}", border_style="cyan", box=box.ROUNDED))
        console.print(f"\n[dim]Save this content to /etc/nginx/sites-available/{domain} on your VPS.[/dim]")
        return

    run_server(port=port, background=bg)


@app.command()
def backup(
    out: str = typer.Option(
        None,
        "--out",
        "-o",
        help="Optional destination path for backup JSON file.",
    )
):
    """Create timestamped local & cloud database backup."""
    initialize_database()
    seed_people()

    target = create_db_backup(out)
    console.print(
        Panel(
            f"[bold green]✓ Database backup successfully created:[/bold green]\n[cyan]{target.resolve()}[/cyan]",
            border_style="green",
            box=box.ROUNDED,
        )
    )


@app.command()
def restore(
    file_path: str = typer.Argument(
        ...,
        help="Path to backup file (.db or .json) to restore from.",
    )
):
    """Restore database from a local backup file or JSON dump."""
    try:
        restore_db_from_file(file_path)
        console.print(
            Panel(
                f"[bold green]✓ Database successfully restored from backup:[/bold green]\n[cyan]{file_path}[/cyan]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
    except Exception as err:
        console.print(f"[red]✗ Failed to restore database: {err}[/red]")
        raise typer.Exit(code=1)


@app.command()
def deploy(
    target: str = typer.Argument(
        ...,
        help="VPS SSH target (e.g., 'user@your-vps-ip' or 'root@123.45.67.89').",
    ),
    port: int = typer.Option(
        8765,
        "--port",
        "-p",
        help="Port to run live dashboard server on VPS.",
    ),
):
    """1-Click automated deployment to host live transparent server on your VPS via SSH."""
    import subprocess

    initialize_database()
    seed_people()

    console.print(f"\n[bold cyan]🚀 Starting 1-Click Automated VPS Deployment to {target}...[/bold cyan]\n")

    setup_script = f"""
set -e
mkdir -p ~/.local/share/tiffin/backups
python3 -m venv ~/.tiffin_env || true
~/.tiffin_env/bin/pip install --upgrade pip rich typer >/dev/null 2>&1
~/.tiffin_env/bin/pip install git+https://github.com/parikar/tiffin.git >/dev/null 2>&1 || ~/.tiffin_env/bin/pip install typer rich >/dev/null 2>&1

pkill -f "tiffin serve" || true
nohup ~/.tiffin_env/bin/python -m tiffin serve --port {port} > ~/.tiffin_server.log 2>&1 &
"""

    try:
        console.print("[dim]• Setting up environment and live server on VPS via SSH...[/dim]")
        proc = subprocess.run(["ssh", target, setup_script], text=True, capture_output=True, timeout=60)
        if proc.returncode != 0 and "Permission denied" in proc.stderr:
            console.print(f"[red]✗ SSH connection failed: {proc.stderr.strip()}[/red]")
            raise typer.Exit(code=1)

        # Upload database
        console.print("[dim]• Uploading current database state to VPS...[/dim]")
        db_json = export_db_to_json()
        upload_script = "cat > ~/.local/share/tiffin/backups/tiffin_backup_latest.json && ~/.tiffin_env/bin/python -c 'from tiffin import backup; backup.restore_db_from_file(\"/home/\" + \"'.split()[0] + \"/.local/share/tiffin/backups/tiffin_backup_latest.json\")' 2>/dev/null || true"
        subprocess.run(["ssh", target, upload_script], input=db_json, text=True, capture_output=True, timeout=15)

        vps_ip = target.split("@")[-1]
        console.print(
            Panel(
                f"[bold green]✓ 1-Click VPS Deployment Complete![/bold green]\n\n"
                f"• [bold]Live Website for Friends:[/bold] [cyan]http://{vps_ip}:{port}[/cyan]\n"
                f"• [bold]Auto-Sync Setting for your laptop:[/bold]\n"
                f"  Add this to your ~/.bashrc or shell profile:\n"
                f"  [yellow]export TIFFIN_SERVER_URL=\"http://{vps_ip}:{port}\"[/yellow]\n\n"
                f"Every time you run [bold]tiffin record[/bold] locally, it will auto-update your VPS live server instantly!",
                title="🚀 Deployment Successful",
                border_style="green",
                box=box.ROUNDED,
            )
        )
    except Exception as err:
        console.print(f"[red]✗ Deployment error: {err}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
