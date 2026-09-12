import unittest
import tempfile
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import patch

from tiffin import db, settlement_db, input as input_mod, reports, billing, export, formatting


class TestTiffinCore(unittest.TestCase):

    def setUp(self):
        # Create a temporary database file for isolated testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = Path(self.temp_dir.name) / "test_tiffin.db"
        self.db_patch = patch.object(db, "DB_PATH", self.db_file)
        self.db_patch.start()

        db.initialize_database()
        db.seed_people()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_database_initialization_and_seeding(self):
        people = db.get_people()
        names = [p[1] for p in people]
        self.assertIn("Parikar", names)
        self.assertIn("Abhay", names)
        self.assertIn("Ashutosh", names)
        self.assertIn("Atharva", names)

    def test_save_and_retrieve_consumption(self):
        today_str = date.today().isoformat()
        people = db.get_people()
        p1_id = people[0][0]

        db.save_consumption(
            date=today_str,
            meal="lunch",
            person_id=p1_id,
            ate=True,
            description="Regular",
            price_paise=7000,
        )

        rows = db.get_consumption_for_date(today_str)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "lunch")
        self.assertEqual(rows[0][1], p1_id)
        self.assertTrue(rows[0][3])
        self.assertEqual(rows[0][5], 7000)

    def test_consumption_upsert_update(self):
        today_str = date.today().isoformat()
        people = db.get_people()
        p1_id = people[0][0]

        # Initial insert
        db.save_consumption(today_str, "lunch", p1_id, True, "Regular", 7000)
        # Edit/Update record
        db.save_consumption(today_str, "lunch", p1_id, True, "Special", 10000)

        rows = db.get_consumption_for_date(today_str)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][4], "Special")
        self.assertEqual(rows[0][5], 10000)

    def test_delete_consumption_record(self):
        today_str = date.today().isoformat()
        people = db.get_people()
        p1_id = people[0][0]

        db.save_consumption(today_str, "lunch", p1_id, True, "Regular", 7000)
        db.save_consumption(today_str, "dinner", p1_id, True, "Regular", 7000)

        # Delete lunch only
        deleted_count = db.delete_consumption_record(today_str, "lunch")
        self.assertEqual(deleted_count, 1)

        rows = db.get_consumption_for_date(today_str)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "dinner")

    def test_settlements_and_billing(self):
        today_str = date.today().isoformat()
        people = db.get_people()
        p1_id = people[0][0]

        # Record 2 meals
        db.save_consumption(today_str, "lunch", p1_id, True, "Regular", 7000)
        db.save_consumption(today_str, "dinner", p1_id, True, "Regular", 7000)

        # Record settlement payment of 5000 paise (₹50)
        settlement_db.record_settlement(p1_id, 5000, today_str, "UPI payment")

        bill_info = billing.get_person_bill(p1_id)
        self.assertEqual(bill_info["tiffins_count"], 2)
        self.assertEqual(bill_info["total_cost_paise"], 14000)
        self.assertEqual(bill_info["total_settled_paise"], 5000)
        self.assertEqual(bill_info["pending_paise"], 9000)

    def test_input_date_parsing(self):
        today_str = date.today().isoformat()
        yesterday_str = (date.today() - timedelta(days=1)).isoformat()

        self.assertEqual(input_mod.parse_date("today"), today_str)
        self.assertEqual(input_mod.parse_date(""), today_str)
        self.assertEqual(input_mod.parse_date("yesterday"), yesterday_str)

    def test_input_price_parsing(self):
        self.assertEqual(input_mod.parse_price("70"), 7000)
        self.assertEqual(input_mod.parse_price("70.50"), 7050)
        self.assertEqual(input_mod.parse_price("₹100"), 10000)
        self.assertEqual(input_mod.parse_price(""), 7000)

        with self.assertRaises(ValueError):
            input_mod.parse_price("-50")

    def test_detailed_report_generation(self):
        today_str = date.today().isoformat()
        people = db.get_people()
        p1_id = people[0][0]

        db.save_consumption(today_str, "lunch", p1_id, True, "Regular", 7000)
        db.save_consumption(today_str, "dinner", p1_id, True, "Special", 9000)

        report_data = reports.get_month_report(today_str, today_str)

        # Check 6 sections existence
        self.assertIn("overview", report_data)
        self.assertIn("lunch_vs_dinner", report_data)
        self.assertIn("people", report_data)
        self.assertIn("daily", report_data)
        self.assertIn("specials", report_data)
        self.assertIn("unrecorded", report_data)

        self.assertEqual(report_data["overview"]["total_tiffins"], 2)
        self.assertEqual(report_data["overview"]["total_cost_paise"], 16000)
        self.assertEqual(report_data["overview"]["avg_per_tiffin_paise"], 8000)

    def test_csv_and_whatsapp_export(self):
        today_str = date.today().isoformat()
        people = db.get_people()
        p1_id = people[0][0]
        db.save_consumption(today_str, "lunch", p1_id, True, "Regular", 7000)

        month_data = reports.get_month_report(today_str, today_str)

        out_csv = Path(self.temp_dir.name) / "test_report.csv"
        export.export_month_to_csv(month_data, out_csv)
        self.assertTrue(out_csv.exists())

        wa_text = export.generate_whatsapp_summary(p1_id)
        self.assertIn("Tiffin Bill Statement", wa_text)

    def test_daily_history_matrix_generation(self):
        today_str = date.today().isoformat()
        people = db.get_people()
        p1_id, p1_name = people[0][0], people[0][1]
        p2_id, p2_name = people[1][0], people[1][1]

        # Record lunch and dinner with ate=True/False and Regular/Special
        db.save_consumption(today_str, "lunch", p1_id, True, "Regular", 7000)
        db.save_consumption(today_str, "dinner", p1_id, True, "Special", 9000)
        db.save_consumption(today_str, "lunch", p2_id, False, None, None)

        history_data = reports.get_daily_history_matrix(today_str, today_str)

        self.assertIn("rows", history_data)
        self.assertIn("person_stats", history_data)
        self.assertEqual(len(history_data["rows"]), 1)

        row = history_data["rows"][0]
        self.assertEqual(row["date"], today_str)

        p1_lunch = row["persons"][p1_id]["lunch"]
        self.assertTrue(p1_lunch["ate"])
        self.assertEqual(p1_lunch["description"], "Regular")

        p1_dinner = row["persons"][p1_id]["dinner"]
        self.assertTrue(p1_dinner["ate"])
        self.assertEqual(p1_dinner["description"], "Special")

        p2_lunch = row["persons"][p2_id]["lunch"]
        self.assertFalse(p2_lunch["ate"])

        stats1 = history_data["person_stats"][p1_id]
        self.assertEqual(stats1["total_ate"], 2)
        self.assertEqual(stats1["regular_count"], 1)
        self.assertEqual(stats1["special_count"], 1)

    def test_history_csv_and_html_export(self):
        today_str = date.today().isoformat()
        people = db.get_people()
        p1_id = people[0][0]

        db.save_consumption(today_str, "lunch", p1_id, True, "Special", 9000)
        history_data = reports.get_daily_history_matrix(today_str, today_str)

        csv_file = Path(self.temp_dir.name) / "history.csv"
        html_file = Path(self.temp_dir.name) / "history.html"

        export.export_history_to_csv(history_data, csv_file)
        export.export_history_to_html(history_data, html_file)

        self.assertTrue(csv_file.exists())
        self.assertTrue(html_file.exists())

        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Tiffin Attendance Transparency Dashboard", content)

    def test_auto_backup_and_restore(self):
        from tiffin import backup

        today_str = date.today().isoformat()
        people = db.get_people()
        p1_id = people[0][0]

        # Saving consumption triggers auto_backup
        db.save_consumption(today_str, "lunch", p1_id, True, "Regular", 7000)

        backup_file = Path(self.temp_dir.name) / "custom_backup.json"
        target = backup.create_db_backup(backup_file)
        self.assertTrue(target.exists())

        # Modify database then restore
        db.save_consumption(today_str, "lunch", p1_id, False, None, None)
        rows_modified = db.get_consumption_for_date(today_str)
        self.assertFalse(rows_modified[0][3])

        backup.restore_db_from_file(target)
        rows_restored = db.get_consumption_for_date(today_str)
        self.assertTrue(rows_restored[0][3])
        self.assertEqual(rows_restored[0][5], 7000)


if __name__ == "__main__":
    unittest.main()
