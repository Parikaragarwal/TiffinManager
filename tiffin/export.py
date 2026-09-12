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
                l_cells += '<td><span class="badge badge-none">—</span></td>'
            elif not info["ate"]:
                l_cells += '<td><span class="badge badge-no">✗ Didn\'t Eat</span></td>'
            else:
                desc = info.get("description") or "Regular"
                if desc.lower() == "special":
                    l_cells += '<td><span class="badge badge-special">★ Ate (Special)</span></td>'
                else:
                    l_cells += '<td><span class="badge badge-yes">✓ Ate (Regular)</span></td>'

        table_rows_html += f"<tr><td><span class=\"date-val\">{d_str}</span></td><td><span class=\"meal-tag lunch\">☀️ Lunch</span></td>{l_cells}</tr>"

        # Dinner row
        d_cells = ""
        for p_id, _ in people:
            info = r["persons"].get(p_id, {}).get("dinner")
            if not info:
                d_cells += '<td><span class="badge badge-none">—</span></td>'
            elif not info["ate"]:
                d_cells += '<td><span class="badge badge-no">✗ Didn\'t Eat</span></td>'
            else:
                desc = info.get("description") or "Regular"
                if desc.lower() == "special":
                    d_cells += '<td><span class="badge badge-special">★ Ate (Special)</span></td>'
                else:
                    d_cells += '<td><span class="badge badge-yes">✓ Ate (Regular)</span></td>'

        table_rows_html += f'<tr class="dinner-row"><td><span class="date-val dim">{d_str}</span></td><td><span class="meal-tag dinner">🌙 Dinner</span></td>{d_cells}</tr>'

    stats_cards_html = ""
    for p_id, s in person_stats.items():
        cost_inr = f"₹{s['total_cost_paise'] / 100:.2f}"
        stats_cards_html += f"""
        <div class="card">
            <div class="card-header">
                <h3>{s['name']}</h3>
                <span class="total-badge">{cost_inr}</span>
            </div>
            <div class="stat-num">{s['total_ate']} <small>tiffins</small></div>
            <div class="stat-detail">
                <div class="stat-pill">☀️ Lunch: <strong>{s['lunch_ate']}</strong></div>
                <div class="stat-pill">🌙 Dinner: <strong>{s['dinner_ate']}</strong></div>
                <div class="stat-pill special-pill">★ Special: <strong>{s['special_count']}</strong></div>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🍱 Tiffin Transparency Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root[data-theme="dark"] {{
            --bg: #0b0f19;
            --panel: rgba(22, 30, 46, 0.75);
            --panel-border: rgba(255, 255, 255, 0.1);
            --text: #f8fafc;
            --text-sub: #94a3b8;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.25);
            --card-bg: rgba(30, 41, 59, 0.65);
            --table-header: rgba(15, 23, 42, 0.85);
            --table-row-alt: rgba(15, 23, 42, 0.4);
            --badge-yes-bg: rgba(16, 185, 129, 0.15);
            --badge-yes-text: #34d399;
            --badge-yes-border: rgba(16, 185, 129, 0.35);
            --badge-special-bg: rgba(245, 158, 11, 0.18);
            --badge-special-text: #fbbf24;
            --badge-special-border: rgba(245, 158, 11, 0.45);
            --badge-no-bg: rgba(239, 68, 68, 0.15);
            --badge-no-text: #f87171;
            --badge-no-border: rgba(239, 68, 68, 0.3);
            --badge-none-text: #64748b;
        }}

        :root[data-theme="light"] {{
            --bg: #f1f5f9;
            --panel: rgba(255, 255, 255, 0.85);
            --panel-border: rgba(0, 0, 0, 0.08);
            --text: #0f172a;
            --text-sub: #64748b;
            --accent: #0284c7;
            --accent-glow: rgba(2, 132, 199, 0.15);
            --card-bg: rgba(255, 255, 255, 0.9);
            --table-header: #e2e8f0;
            --table-row-alt: rgba(241, 245, 249, 0.6);
            --badge-yes-bg: rgba(16, 185, 129, 0.12);
            --badge-yes-text: #059669;
            --badge-yes-border: rgba(16, 185, 129, 0.3);
            --badge-special-bg: rgba(245, 158, 11, 0.14);
            --badge-special-text: #d97706;
            --badge-special-border: rgba(245, 158, 11, 0.35);
            --badge-no-bg: rgba(239, 68, 68, 0.12);
            --badge-no-text: #dc2626;
            --badge-no-border: rgba(239, 68, 68, 0.25);
            --badge-none-text: #94a3b8;
        }}

        * {{
            box-sizing: border-box;
            transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
        }}

        body {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 32px 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1240px;
            margin: 0 auto;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 36px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--panel-border);
        }}

        .title-group h1 {{
            font-size: 2.2rem;
            font-weight: 800;
            margin: 0 0 6px 0;
            background: linear-gradient(135deg, var(--text) 30%, var(--accent) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
        }}

        .title-group p {{
            margin: 0;
            color: var(--text-sub);
            font-size: 0.95rem;
            font-weight: 500;
        }}

        .theme-toggle-btn {{
            background: var(--panel);
            border: 1px solid var(--panel-border);
            color: var(--text);
            padding: 10px 18px;
            border-radius: 999px;
            cursor: pointer;
            font-family: inherit;
            font-weight: 600;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }}
        .theme-toggle-btn:hover {{
            transform: translateY(-2px);
            border-color: var(--accent);
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 36px;
        }}

        .card {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--panel-border);
            border-radius: 16px;
            padding: 22px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        }}
        .card:hover {{
            transform: translateY(-3px);
            border-color: var(--accent);
        }}

        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}

        .card-header h3 {{
            margin: 0;
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text);
        }}

        .total-badge {{
            background: var(--accent-glow);
            color: var(--accent);
            font-weight: 700;
            font-size: 0.85rem;
            padding: 4px 10px;
            border-radius: 999px;
        }}

        .stat-num {{
            font-size: 2.2rem;
            font-weight: 800;
            color: var(--text);
            line-height: 1.1;
            margin-bottom: 14px;
        }}
        .stat-num small {{
            font-size: 0.95rem;
            color: var(--text-sub);
            font-weight: 500;
        }}

        .stat-detail {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .stat-pill {{
            background: var(--table-header);
            padding: 5px 10px;
            border-radius: 8px;
            font-size: 0.82rem;
            color: var(--text-sub);
            font-weight: 500;
        }}
        .special-pill {{
            color: var(--badge-special-text);
        }}

        .table-container {{
            background: var(--panel);
            backdrop-filter: blur(12px);
            border-radius: 20px;
            border: 1px solid var(--panel-border);
            overflow: hidden;
            box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.15);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: center;
        }}

        th, td {{
            padding: 14px 18px;
            font-size: 0.92rem;
        }}

        th {{
            background: var(--table-header);
            color: var(--accent);
            font-weight: 700;
            font-size: 0.95rem;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }}

        td {{
            border-bottom: 1px solid var(--panel-border);
        }}

        tr.dinner-row {{
            background-color: var(--table-row-alt);
        }}

        .date-val {{
            font-weight: 700;
            color: var(--text);
        }}

        .meal-tag {{
            font-size: 0.82rem;
            padding: 5px 12px;
            border-radius: 999px;
            font-weight: 700;
            display: inline-block;
        }}
        .meal-tag.lunch {{
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent);
        }}
        .meal-tag.dinner {{
            background: rgba(192, 132, 252, 0.15);
            color: #c084fc;
        }}

        .badge {{
            display: inline-block;
            padding: 6px 14px;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 700;
        }}
        .badge-yes {{
            background: var(--badge-yes-bg);
            color: var(--badge-yes-text);
            border: 1px solid var(--badge-yes-border);
        }}
        .badge-special {{
            background: var(--badge-special-bg);
            color: var(--badge-special-text);
            border: 1px solid var(--badge-special-border);
            box-shadow: 0 0 12px var(--badge-special-bg);
        }}
        .badge-no {{
            background: var(--badge-no-bg);
            color: var(--badge-no-text);
            border: 1px solid var(--badge-no-border);
        }}
        .badge-none {{
            color: var(--badge-none-text);
        }}

        .dim {{
            color: var(--text-sub);
            font-weight: 500;
        }}

        @media (max-width: 768px) {{
            body {{ padding: 16px 12px; }}
            header {{ flex-direction: column; align-items: flex-start; gap: 14px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="title-group">
                <h1>🍱 Tiffin Attendance Transparency Dashboard</h1>
                <p>Live transparent meal records for flatmates & friends</p>
            </div>
            <button class="theme-toggle-btn" onclick="toggleTheme()">
                <span id="theme-icon">🌙</span> <span id="theme-text">Dark Mode</span>
            </button>
        </header>

        <div class="grid">
            {stats_cards_html}
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Meal Slot</th>
                        {table_headers_html}
                    </tr>
                </thead>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function setTheme(theme) {{
            document.documentElement.setAttribute('data-theme', theme);
            const icon = document.getElementById('theme-icon');
            const text = document.getElementById('theme-text');
            if (theme === 'light') {{
                icon.textContent = '☀️';
                text.textContent = 'Light Mode';
            }} else {{
                icon.textContent = '🌙';
                text.textContent = 'Dark Mode';
            }}
            localStorage.setItem('tiffin-theme', theme);
        }}

        function toggleTheme() {{
            const current = document.documentElement.getAttribute('data-theme');
            setTheme(current === 'light' ? 'dark' : 'light');
        }}

        const savedTheme = localStorage.getItem('tiffin-theme') || 'dark';
        setTheme(savedTheme);
    </script>
</body>
</html>
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return path


