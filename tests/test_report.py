import tempfile
import unittest
from pathlib import Path

from appstore_top30 import config, db, report


def _row(app_id, rank):
    return {
        "app_id": app_id,
        "rank": rank,
        "name": f"App {app_id}",
        "developer": "Dev",
        "price_amount": 0.0,
        "currency": "USD",
        "rating": 4.5,
        "rating_count": 100,
        "genre_id": "6014",
        "genre_name": "Games",
    }


class ReportTest(unittest.TestCase):
    def test_generate_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "data" / "test.db"
            reports_dir = root / "reports"
            db.init_db(db_path)
            conn = db.connect(db_path)
            try:
                with conn:
                    db.replace_snapshot(
                        conn,
                        "2026-08-04",
                        "us",
                        "us",
                        "free",
                        "6014",
                        "Games",
                        [_row(1, 1), _row(2, 2)],
                        "2026-08-04T00:00:00+08:00",
                    )
            finally:
                conn.close()

            html_path = report.generate_report("2026-08-04", db_path, reports_dir)
            self.assertTrue(html_path.exists())
            self.assertTrue((reports_dir / "2026-08-04" / "summary.csv").exists())
            self.assertFalse((reports_dir / "2026-08-04" / "region_summary.csv").exists())
            self.assertTrue((reports_dir / "2026-08-04" / "rankings_us_free.csv").exists())
            html = html_path.read_text(encoding="utf-8")
            self.assertIn("App Store Top 30", html)
            self.assertNotIn("地区汇总", html)


if __name__ == "__main__":
    unittest.main()
