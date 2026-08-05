import tempfile
import unittest
from datetime import date
from pathlib import Path

from appstore_top30 import analyze, db


def _row(app_id, rank, genre="6014", rating=4.0, price=0.0, icon_url=None):
    return {
        "app_id": app_id,
        "rank": rank,
        "rank_no": rank,
        "name": f"App {app_id}",
        "developer": "Dev",
        "price_amount": price,
        "currency": "USD",
        "rating": rating,
        "rating_count": 10,
        "genre_id": genre,
        "genre_name": "Games",
        "icon_url": icon_url or f"icon-{app_id}.png",
    }


def _play_row(app_id, rank, category="GAME", rating=4.0, price=0.0, icon_url=None):
    return {
        "app_id": app_id,
        "rank": rank,
        "rank_no": rank,
        "name": f"Play App {app_id}",
        "developer": "Dev",
        "price_amount": price,
        "currency": "USD",
        "rating": rating,
        "rating_count": None,
        "genre_id": category,
        "genre_name": "Games",
        "icon_url": icon_url or f"icon-{app_id}.png",
    }


class AnalyzeTest(unittest.TestCase):
    def test_compare_rankings(self):
        prev_rows = [_row(1, 1), _row(2, 2), _row(3, 3), _row(4, 4)]
        curr_rows = [_row(1, 3), _row(2, 1), _row(3, 4), _row(5, 5)]
        changes = {c["app_id"]: c for c in analyze.compare_rankings(prev_rows, curr_rows)}

        self.assertEqual(changes[1]["status"], "down")
        self.assertEqual(changes[1]["rank_change"], -2)
        self.assertEqual(changes[2]["status"], "up")
        self.assertEqual(changes[2]["rank_change"], 1)
        self.assertEqual(changes[4]["status"], "left")
        self.assertEqual(changes[5]["status"], "new")

    def test_build_country_chart_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            db.init_db(db_path)
            conn = db.connect(db_path)
            try:
                for day, rows in [
                    (date(2026, 8, 3), [_row(1, 1), _row(2, 2), _row(3, 3)]),
                    (date(2026, 8, 4), [_row(2, 1), _row(1, 2), _row(4, 3)]),
                ]:
                    with conn:
                        db.replace_snapshot(
                            conn,
                            day.isoformat(),
                            "us",
                            "us",
                            "free",
                            "6014",
                            "Games",
                            rows,
                            "2026-08-04T00:00:00+08:00",
                        )

                summary = analyze.build_country_chart_summary(
                    conn, "2026-08-04", "2026-08-03", "us", "free"
                )
                self.assertEqual(summary["entries"], 3)
                self.assertEqual(summary["new"], 1)
                self.assertEqual(summary["left"], 1)
                self.assertEqual(summary["up"], 1)
                self.assertEqual(summary["down"], 1)
            finally:
                conn.close()

    def test_build_country_chart_summary_for_play(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            db.init_db(db_path)
            conn = db.connect(db_path)
            try:
                for day, rows in [
                    (date(2026, 8, 4), [_play_row("com.example.a", 1), _play_row("com.example.b", 2)]),
                    (date(2026, 8, 5), [_play_row("com.example.b", 1), _play_row("com.example.c", 2)]),
                ]:
                    with conn:
                        db.replace_play_snapshot(
                            conn,
                            day.isoformat(),
                            "us",
                            "us",
                            "free",
                            "GAME",
                            "Games",
                            rows,
                            "2026-08-05T00:00:00+08:00",
                        )

                summary = analyze.build_country_chart_summary(
                    conn, "2026-08-05", "2026-08-04", "us", "free", store="play"
                )
                self.assertEqual(summary["entries"], 2)
                self.assertEqual(summary["new"], 1)
                self.assertEqual(summary["left"], 1)
                self.assertEqual(summary["genres"], 1)
            finally:
                conn.close()

if __name__ == "__main__":
    unittest.main()
