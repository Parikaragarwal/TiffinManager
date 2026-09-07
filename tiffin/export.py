import csv
from pathlib import Path
from .billing import get_overall_bill, get_person_bill
from .formatting import format_rupees, display_full_date


def export_month_to_csv(report_data: dict, filepath: str | Path) -> Path:
    """Export a month/range report to a CSV file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Person ID", "Name", "Total Tiffins", "Lunch", "Dinner", "Regular", "Special", "Cost (Paise)", "Cost (INR)"])

        for person_id, data in report_data.get("people", {}).items():
            regular_cnt = data.get("tiffins", 0) - data.get("special", 0)
            writer.writerow([
                person_id,
                data["name"],
                data["tiffins"],
                data["lunch"],
                data["dinner"],
                regular_cnt,
                data["special"],
                data["cost_paise"],
                f"{data['cost_paise'] / 100:.2f}",
            ])

        writer.writerow([])
        overview = report_data.get("overview", {})
        writer.writerow([
            "TOTAL OVERVIEW",
            "",
            overview.get("total_tiffins", 0),
            overview.get("recorded_lunches", 0),
            overview.get("recorded_dinners", 0),
            overview.get("regular", 0),
            overview.get("special", 0),
            overview.get("total_cost_paise", 0),
            f"{overview.get('total_cost_paise', 0) / 100:.2f}",
        ])

    return path


def export_bill_to_csv(filepath: str | Path) -> Path:
    """Export overall billing balances to a CSV file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    bill = get_overall_bill()

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Person ID", "Name", "Tiffins Eaten", "Total Cost (INR)", "Total Settled (INR)", "Pending Dues (INR)"])

        for b in bill["balances"]:
            writer.writerow([
                b["person_id"],
                b["name"],
                b["tiffins"],
                f"{b['total_cost_paise'] / 100:.2f}",
                f"{b['total_settled_paise'] / 100:.2f}",
                f"{b['pending_paise'] / 100:.2f}",
            ])

        writer.writerow([])
        writer.writerow([
            "TOTAL",
            "",
            bill["total_tiffins"],
            f"{bill['total_cost_paise'] / 100:.2f}",
            f"{bill['total_settled_paise'] / 100:.2f}",
            f"{bill['total_pending_paise'] / 100:.2f}",
        ])

    return path


def generate_whatsapp_summary(person_id: int | None = None) -> str:
    """Generate a clean, copy-pasteable plain text bill summary for WhatsApp."""
    if person_id is not None:
        p_bill = get_person_bill(person_id)
        lines = [
            f"🍱 *Tiffin Bill Statement - {p_bill['name']}*",
            "--------------------------------",
            f"Tiffins Eaten: {p_bill['tiffins_count']}",
            f"Total Bill: {format_rupees(p_bill['total_cost_paise'])}",
            f"Amount Paid: {format_rupees(p_bill['total_settled_paise'])}",
            f"Pending Balance: *{format_rupees(p_bill['pending_paise'])}*",
            "--------------------------------",
            "Thank you! 🙏",
        ]
        return "\n".join(lines)

    overall = get_overall_bill()
    lines = [
        "🍱 *Tiffin Dues Summary*",
        "--------------------------------",
    ]
    for b in overall["balances"]:
        lines.append(
            f"• *{b['name']}*: {format_rupees(b['total_cost_paise'])} (Paid: {format_rupees(b['total_settled_paise'])} | Due: *{format_rupees(b['pending_paise'])}*)"
        )
    lines.extend([
        "--------------------------------",
        f"Total Tiffins: {overall['total_tiffins']}",
        f"Total Cost: {format_rupees(overall['total_cost_paise'])}",
        f"Total Paid: {format_rupees(overall['total_settled_paise'])}",
        f"Total Dues: *{format_rupees(overall['total_pending_paise'])}*",
    ])
    return "\n".join(lines)
