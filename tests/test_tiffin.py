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

    def test_learned_ate_default(self):
        self.assertTrue(input_mod.get_learned_ate_default([]))
        self.assertTrue(input_mod.get_learned_ate_default([True, True]))
        self.assertTrue(input_mod.get_learned_ate_default([True, True, False]))
        self.assertFalse(input_mod.get_learned_ate_default([False, False, False]))

    def test_report_scopes_unsettled_month_all(self):
        today_str = date.today().isoformat()
        past_str = "2026-08-01"
        people = db.get_people()
        p1_id = people[0][0]

        db.save_consumption(past_str, "lunch", p1_id, True, "Regular", 7000)
        db.save_consumption(today_str, "lunch", p1_id, True, "Regular", 7000)

        start_unsettled, end_unsettled, label_unsettled = reports.parse_date_range(scope="unsettled")
        self.assertEqual(start_unsettled, past_str)

        start_all, end_all, label_all = reports.parse_date_range(scope="all")
        self.assertEqual(start_all, past_str)

        month_data = reports.get_month_report(start_unsettled, end_unsettled)
        self.assertEqual(month_data["overview"]["tiffins"], 2)

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


if __name__ == "__main__":
    unittest.main()
