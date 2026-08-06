import tempfile
import unittest
from pathlib import Path

from appstore_top30 import dashboard, db


def _app_row(app_id, rank, genre_id, genre_name):
    return {
        "app_id": app_id,
        "rank": rank,
        "name": f"App {app_id}",
        "developer": "Dev",
        "price_amount": 0.0,
        "currency": "USD",
        "rating": 4.0,
        "rating_count": 10,
        "genre_id": genre_id,
        "genre_name": genre_name,
    }


def _play_row(app_id, rank):
    return {
        "app_id": app_id,
        "rank": rank,
        "name": f"App {app_id}",
        "developer": "Dev",
        "price_amount": 0.0,
        "currency": "USD",
        "rating": 4.0,
        "rating_count": 10,
    }


class DashboardTest(unittest.TestCase):
    def test_appstore_distribution_counts_unique_apps(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            db.init_db(db_path)
            conn = db.connect(db_path)
            try:
                with conn:
                    db.replace_snapshot(
                        conn,
                        "2026-08-05",
                        "north_america",
                        "us",
                        "free",
                        "6000",
                        "商务",
                        [
                            _app_row(1, 1, "6000", "商务"),
                            _app_row(2, 2, "6000", "商务"),
                            _app_row(3, 3, "6000", "商务"),
                        ],
                        "2026-08-05T00:00:00+08:00",
                    )
                    db.replace_snapshot(
                        conn,
                        "2026-08-05",
                        "north_america",
                        "us",
                        "free",
                        "6014",
                        "游戏",
                        [
                            _app_row(2, 1, "6014", "游戏"),
                            _app_row(3, 2, "6014", "游戏"),
                            _app_row(4, 3, "6014", "游戏"),
                        ],
                        "2026-08-05T00:00:00+08:00",
                    )
                items = dashboard.query_category_distribution(
                    conn, "2026-08-05", "us", "free", store="app_store"
                )
                counts = {item["genre_id"]: item["apps"] for item in items}
                self.assertEqual(counts["6000"], 3)
                self.assertEqual(counts["6014"], 3)
            finally:
                conn.close()

    def test_distribution_filters_by_app_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            db.init_db(db_path)
            conn = db.connect(db_path)
            try:
                with conn:
                    db.replace_snapshot(
                        conn,
                        "2026-08-05",
                        "north_america",
                        "us",
                        "free",
                        "6000",
                        "商务",
                        [
                            _app_row(1, 1, "6000", "商务"),
                            _app_row(2, 2, "6000", "商务"),
                            _app_row(3, 3, "6000", "商务"),
                        ],
                        "2026-08-05T00:00:00+08:00",
                    )
                    db.replace_snapshot(
                        conn,
                        "2026-08-05",
                        "north_america",
                        "us",
                        "free",
                        "6014",
                        "游戏",
                        [
                            _app_row(2, 1, "6014", "游戏"),
                            _app_row(3, 2, "6014", "游戏"),
                            _app_row(4, 3, "6014", "游戏"),
                        ],
                        "2026-08-05T00:00:00+08:00",
                    )
                items = dashboard.query_category_distribution(
                    conn,
                    "2026-08-05",
                    "us",
                    "free",
                    store="app_store",
                    app_ids=["1", "2"],
                )
                counts = {item["genre_id"]: item["apps"] for item in items}
                self.assertEqual(counts["6000"], 2)
                self.assertEqual(counts["6014"], 1)
            finally:
                conn.close()

    def test_play_distribution_counts_unique_apps(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            db.init_db(db_path)
            conn = db.connect(db_path)
            try:
                with conn:
                    db.replace_play_snapshot(
                        conn,
                        "2026-08-05",
                        "north_america",
                        "us",
                        "free",
                        "GAME_ACTION",
                        "动作",
                        [_play_row("com.a", 1), _play_row("com.b", 2)],
                        "2026-08-05T00:00:00+08:00",
                    )
                    db.replace_play_snapshot(
                        conn,
                        "2026-08-05",
                        "north_america",
                        "us",
                        "free",
                        "GAME_CARD",
                        "卡牌",
                        [_play_row("com.b", 1), _play_row("com.c", 2)],
                        "2026-08-05T00:00:00+08:00",
                    )
                items = dashboard.query_category_distribution(
                    conn, "2026-08-05", "us", "free", store="play"
                )
                counts = {item["genre_id"]: item["apps"] for item in items}
                self.assertEqual(counts["GAME_ACTION"], 2)
                self.assertEqual(counts["GAME_CARD"], 2)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
