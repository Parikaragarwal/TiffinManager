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


def export_history_to_csv(history_data: dict, filepath: str | Path) -> Path:
    """Export daily attendance & meal type matrix to a CSV file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    people = history_data.get("people", [])
    headers = ["Date", "Meal (Day/Night)"] + [p[1] for p in people]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for row in history_data.get("rows", []):
            d_str = row["date"]
            # Lunch row
            lunch_row = [d_str, "Lunch (Day)"]
            for p_id, _ in people:
                p_info = row["persons"].get(p_id, {})
                l_info = p_info.get("lunch")
                if not l_info:
                    val = "Not Recorded"
                elif not l_info["ate"]:
                    val = "Didn't Eat"
                else:
                    desc = l_info.get("description") or "Regular"
                    val = f"Ate ({desc})"
                lunch_row.append(val)
            writer.writerow(lunch_row)

            # Dinner row
            dinner_row = [d_str, "Dinner (Night)"]
            for p_id, _ in people:
                p_info = row["persons"].get(p_id, {})
                d_info = p_info.get("dinner")
                if not d_info:
                    val = "Not Recorded"
                elif not d_info["ate"]:
                    val = "Didn't Eat"
                else:
                    desc = d_info.get("description") or "Regular"
                    val = f"Ate ({desc})"
                dinner_row.append(val)
            writer.writerow(dinner_row)

        writer.writerow([])
        writer.writerow(["PERSON ATTENDANCE SUMMARY"])
        writer.writerow(["Person", "Total Ate", "Lunch Ate", "Dinner Ate", "Regular Tiffins", "Special Tiffins", "Total Cost (INR)"])
        for p_id, stats in history_data.get("person_stats", {}).items():
            writer.writerow([
                stats["name"],
                stats["total_ate"],
                stats["lunch_ate"],
                stats["dinner_ate"],
                stats["regular_count"],
                stats["special_count"],
                f"{stats['total_cost_paise'] / 100:.2f}",
            ])

    return path


def export_history_to_html(history_data: dict, filepath: str | Path) -> Path:
    """Generate a responsive glassmorphic HTML web dashboard for meal history transparency."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    people = history_data.get("people", [])
    rows = history_data.get("rows", [])
    person_stats = history_data.get("person_stats", {})

    table_headers_html = "".join([f"<th>{p[1]}</th>" for p in people])

    table_rows_html = ""
    for r in rows:
        d_str = r["date"]

        # Lunch row
        l_cells = ""
        for p_id, _ in people:
            info = r["persons"].get(p_id, {}).get("lunch")
            if not info:
                l_cells += '<td class="badge-none">—</td>'
            elif not info["ate"]:
                l_cells += '<td class="badge-no">✗ Didn\'t Eat</td>'
            else:
                desc = info.get("description") or "Regular"
                if desc.lower() == "special":
                    l_cells += '<td class="badge-special">★ Ate (Special)</td>'
                else:
                    l_cells += '<td class="badge-yes">✓ Ate (Regular)</td>'

        table_rows_html += f"<tr><td><strong>{d_str}</strong></td><td><span class=\"meal-tag lunch\">☀️ Lunch</span></td>{l_cells}</tr>"

        # Dinner row
        d_cells = ""
        for p_id, _ in people:
            info = r["persons"].get(p_id, {}).get("dinner")
            if not info:
                d_cells += '<td class="badge-none">—</td>'
            elif not info["ate"]:
                d_cells += '<td class="badge-no">✗ Didn\'t Eat</td>'
            else:
                desc = info.get("description") or "Regular"
                if desc.lower() == "special":
                    d_cells += '<td class="badge-special">★ Ate (Special)</td>'
                else:
                    d_cells += '<td class="badge-yes">✓ Ate (Regular)</td>'

        table_rows_html += f'<tr class="dinner-row"><td><small class="dim">{d_str}</small></td><td><span class="meal-tag dinner">🌙 Dinner</span></td>{d_cells}</tr>'

    stats_cards_html = ""
    for p_id, s in person_stats.items():
        cost_inr = f"₹{s['total_cost_paise'] / 100:.2f}"
        stats_cards_html += f"""
        <div class="card">
            <h3>{s['name']}</h3>
            <div class="stat-num">{s['total_ate']} <small>tiffins</small></div>
            <div class="stat-detail">
                <span>☀️ Lunch: {s['lunch_ate']}</span> • <span>🌙 Dinner: {s['dinner_ate']}</span><br>
                <span>★ Special: {s['special_count']}</span> • <span>Total: {cost_inr}</span>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🍱 Tiffin Transparency Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0f172a;
            --panel: #1e293b;
            --text: #f8fafc;
            --accent: #38bdf8;
            --green: #4ade80;
            --yellow: #facc15;
            --red: #f87171;
            --dim: #94a3b8;
        }}
        body {{
            font-family: 'Inter', sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px;
        }}
        header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        h1 {{
            color: var(--accent);
            font-size: 2rem;
            margin: 0 0 8px 0;
        }}
        p.subtitle {{
            color: var(--dim);
            margin: 0;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }}
        .card {{
            background: var(--panel);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }}
        .card h3 {{
            margin: 0 0 6px 0;
            color: var(--accent);
        }}
        .stat-num {{
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--green);
        }}
        .stat-num small {{
            font-size: 0.9rem;
            color: var(--dim);
        }}
        .stat-detail {{
            font-size: 0.85rem;
            color: var(--dim);
            margin-top: 8px;
        }}
        .table-container {{
            background: var(--panel);
            border-radius: 12px;
            overflow-x: auto;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: center;
        }}
        th, td {{
            padding: 12px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        th {{
            background: rgba(0,0,0,0.3);
            color: var(--accent);
            font-weight: 600;
        }}
        tr.dinner-row {{
            background: rgba(0,0,0,0.15);
        }}
        .meal-tag {{
            font-size: 0.85rem;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 600;
        }}
        .meal-tag.lunch {{ background: rgba(56, 189, 248, 0.15); color: var(--accent); }}
        .meal-tag.dinner {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; }}
        .badge-yes {{ color: var(--green); font-weight: 600; }}
        .badge-special {{ color: var(--yellow); font-weight: 700; }}
        .badge-no {{ color: var(--red); }}
        .badge-none {{ color: var(--dim); opacity: 0.5; }}
        .dim {{ color: var(--dim); }}
    </style>
</head>
<body>
    <header>
        <h1>🍱 Tiffin Attendance Transparency Dashboard</h1>
        <p class="subtitle">Live transparent meal record for flatmates & friends</p>
    </header>

    <div class="grid">
        {stats_cards_html}
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Meal</th>
                    {table_headers_html}
                </tr>
            </thead>
            <tbody>
                {table_rows_html}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return path

