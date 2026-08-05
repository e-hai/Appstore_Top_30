import tempfile
import unittest
from pathlib import Path

from appstore_top30 import db


def _row(app_id, rank):
    return {
        "app_id": app_id,
        "rank": rank,
        "name": f"App {app_id}",
        "developer": "Dev",
        "price_amount": 0.0,
        "currency": "USD",
        "rating": 4.0,
        "rating_count": 10,
        "genre_id": "36",
        "genre_name": "总榜",
    }


class DbTest(unittest.TestCase):
    def test_clear_snapshots_ignores_old_region_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            db.init_db(db_path)
            conn = db.connect(db_path)
            try:
                with conn:
                    db.replace_snapshot(
                        conn,
                        "2026-08-05",
                        "us",
                        "us",
                        "free",
                        "36",
                        "总榜",
                        [_row(1, 1)],
                        "2026-08-05T00:00:00+08:00",
                    )
                    db.replace_snapshot(
                        conn,
                        "2026-08-05",
                        "north_america",
                        "us",
                        "free",
                        "36",
                        "总榜",
                        [_row(1, 1)],
                        "2026-08-05T00:00:00+08:00",
                    )
                db.clear_snapshots(conn, "2026-08-05", ["us"], ["free"])
                count = conn.execute(
                    "SELECT COUNT(*) FROM snapshots WHERE date = '2026-08-05' AND country = 'us'"
                ).fetchone()[0]
                self.assertEqual(count, 0)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
