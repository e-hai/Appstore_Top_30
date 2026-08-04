"""SQLite storage helpers."""

import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS apps (
    app_id INTEGER PRIMARY KEY,
    bundle_id TEXT,
    name TEXT NOT NULL,
    developer TEXT,
    icon_url TEXT,
    first_seen TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    region TEXT NOT NULL,
    country TEXT NOT NULL,
    chart_type TEXT NOT NULL,
    genre_id TEXT NOT NULL,
    genre_name TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    UNIQUE(date, region, country, chart_type, genre_id)
);

CREATE TABLE IF NOT EXISTS rankings (
    snapshot_id INTEGER NOT NULL,
    rank_no INTEGER NOT NULL,
    app_id INTEGER NOT NULL,
    name TEXT,
    developer TEXT,
    price_amount REAL,
    currency TEXT,
    rating REAL,
    rating_count INTEGER,
    PRIMARY KEY (snapshot_id, rank_no),
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY (app_id) REFERENCES apps(app_id)
);

CREATE INDEX IF NOT EXISTS idx_rankings_snapshot ON rankings(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_rankings_app ON rankings(app_id);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(db_path)) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def clear_snapshots(
    conn: sqlite3.Connection,
    date: str,
    regions: list[str],
    charts: list[str],
) -> None:
    """Remove snapshots for a date before a fresh fetch to avoid stale data."""
    placeholders_regions = ",".join("?" for _ in regions)
    placeholders_charts = ",".join("?" for _ in charts)
    with conn:
        conn.execute(
            f"""
            DELETE FROM snapshots
            WHERE date = ? AND region IN ({placeholders_regions}) AND chart_type IN ({placeholders_charts})
            """,
            (date, *regions, *charts),
        )


def replace_snapshot(
    conn: sqlite3.Connection,
    date: str,
    region: str,
    country: str,
    chart_type: str,
    genre_id: str,
    genre_name: str,
    rows: list[dict],
    fetched_at: str,
) -> None:
    """Replace one chart/genre snapshot for a date in a single transaction."""
    with conn:
        for row in rows:
            conn.execute(
                """
                INSERT INTO apps (app_id, bundle_id, name, developer, icon_url, first_seen)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(app_id) DO NOTHING
                """,
                (
                    row["app_id"],
                    row.get("bundle_id"),
                    row.get("name"),
                    row.get("developer"),
                    row.get("icon_url"),
                    date,
                ),
            )

        conn.execute(
            """
            INSERT INTO snapshots (date, region, country, chart_type, genre_id, genre_name, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, region, country, chart_type, genre_id)
            DO UPDATE SET genre_name = excluded.genre_name, fetched_at = excluded.fetched_at
            """,
            (date, region, country, chart_type, genre_id, genre_name, fetched_at),
        )
        snapshot_id = conn.execute(
            """
            SELECT id FROM snapshots
            WHERE date = ? AND region = ? AND country = ? AND chart_type = ? AND genre_id = ?
            """,
            (date, region, country, chart_type, genre_id),
        ).fetchone()["id"]

        conn.execute("DELETE FROM rankings WHERE snapshot_id = ?", (snapshot_id,))
        conn.executemany(
            """
            INSERT INTO rankings
                (snapshot_id, rank_no, app_id, name, developer, price_amount, currency, rating, rating_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    snapshot_id,
                    row["rank"],
                    row["app_id"],
                    row.get("name"),
                    row.get("developer"),
                    row.get("price_amount"),
                    row.get("currency"),
                    row.get("rating"),
                    row.get("rating_count"),
                )
                for row in rows
            ],
        )


def list_dates(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT date FROM snapshots ORDER BY date"
    ).fetchall()
    return [row["date"] for row in rows]


def get_previous_date(conn: sqlite3.Connection, date: str) -> str | None:
    row = conn.execute(
        "SELECT MAX(date) AS d FROM snapshots WHERE date < ?", (date,)
    ).fetchone()
    return row["d"] if row and row["d"] else None


def snapshot_counts(conn: sqlite3.Connection, date: str) -> dict:
    snapshot_count = conn.execute(
        "SELECT COUNT(*) AS n FROM snapshots WHERE date = ?", (date,)
    ).fetchone()["n"]
    entry_count = conn.execute(
        """
        SELECT COUNT(*) AS n
        FROM rankings r JOIN snapshots s ON s.id = r.snapshot_id
        WHERE s.date = ?
        """,
        (date,),
    ).fetchone()["n"]
    country_count = conn.execute(
        "SELECT COUNT(DISTINCT country) AS n FROM snapshots WHERE date = ?", (date,)
    ).fetchone()["n"]
    return {
        "snapshots": snapshot_count,
        "entries": entry_count,
        "countries": country_count,
    }
