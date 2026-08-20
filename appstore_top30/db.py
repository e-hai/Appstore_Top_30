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

CREATE TABLE IF NOT EXISTS play_apps (
    package_name TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    developer TEXT,
    icon_url TEXT,
    first_seen TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS play_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    region TEXT NOT NULL,
    country TEXT NOT NULL,
    chart_type TEXT NOT NULL,
    category_id TEXT NOT NULL,
    category_name TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    UNIQUE(date, region, country, chart_type, category_id)
);

CREATE TABLE IF NOT EXISTS play_rankings (
    snapshot_id INTEGER NOT NULL,
    rank_no INTEGER NOT NULL,
    package_name TEXT NOT NULL,
    name TEXT,
    developer TEXT,
    price_amount REAL,
    currency TEXT,
    rating REAL,
    rating_count INTEGER,
    PRIMARY KEY (snapshot_id, rank_no),
    FOREIGN KEY (snapshot_id) REFERENCES play_snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY (package_name) REFERENCES play_apps(package_name)
);

CREATE INDEX IF NOT EXISTS idx_play_rankings_snapshot ON play_rankings(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_play_rankings_app ON play_rankings(package_name);
CREATE INDEX IF NOT EXISTS idx_snapshots_lookup ON snapshots(date, country, chart_type, genre_id);
CREATE INDEX IF NOT EXISTS idx_play_snapshots_lookup ON play_snapshots(date, country, chart_type, category_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_date_country ON snapshots(date, country, chart_type);
CREATE INDEX IF NOT EXISTS idx_play_snapshots_date_country ON play_snapshots(date, country, chart_type);
CREATE INDEX IF NOT EXISTS idx_rankings_app_lookup ON rankings(app_id, snapshot_id);
CREATE INDEX IF NOT EXISTS idx_play_rankings_app_lookup ON play_rankings(package_name, snapshot_id);

CREATE TABLE IF NOT EXISTS app_metadata (
    app_id TEXT PRIMARY KEY,
    store TEXT NOT NULL,
    version TEXT,
    release_date TEXT,
    release_notes TEXT,
    seller_name TEXT,
    primary_genre TEXT,
    updated_at TEXT NOT NULL
);
"""


def save_app_metadata(conn: sqlite3.Connection, meta: dict) -> None:
    """Save or update empirical app metadata to local database."""
    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO app_metadata (app_id, store, version, release_date, release_notes, seller_name, primary_genre, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(app_id) DO UPDATE SET
            version = excluded.version,
            release_date = excluded.release_date,
            release_notes = excluded.release_notes,
            seller_name = excluded.seller_name,
            primary_genre = excluded.primary_genre,
            updated_at = excluded.updated_at
        """,
        (
            str(meta.get("app_id", "")),
            meta.get("store", "app_store"),
            meta.get("version", ""),
            meta.get("release_date", ""),
            meta.get("release_notes", ""),
            meta.get("seller_name", ""),
            meta.get("primary_genre", ""),
            now_str,
        ),
    )


def get_app_metadata(conn: sqlite3.Connection, app_id: str) -> dict | None:
    """Retrieve app metadata from local database."""
    row = conn.execute(
        "SELECT * FROM app_metadata WHERE app_id = ?", (str(app_id),)
    ).fetchone()
    if row:
        return dict(row)
    return None


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


def count_snapshots(
    conn: sqlite3.Connection,
    date: str,
    countries: list[str],
    charts: list[str],
) -> int:
    """Count existing snapshots for a date, countries, and chart types."""
    if not countries or not charts:
        return 0
    placeholders_countries = ",".join("?" for _ in countries)
    placeholders_charts = ",".join("?" for _ in charts)
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS cnt FROM snapshots
        WHERE date = ? AND country IN ({placeholders_countries}) AND chart_type IN ({placeholders_charts})
        """,
        (date, *countries, *charts),
    ).fetchone()
    return int(row["cnt"]) if row else 0


def count_play_snapshots(
    conn: sqlite3.Connection,
    date: str,
    countries: list[str],
    charts: list[str],
) -> int:
    """Count existing Google Play snapshots for a date, countries, and chart types."""
    if not countries or not charts:
        return 0
    placeholders_countries = ",".join("?" for _ in countries)
    placeholders_charts = ",".join("?" for _ in charts)
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS cnt FROM play_snapshots
        WHERE date = ? AND country IN ({placeholders_countries}) AND chart_type IN ({placeholders_charts})
        """,
        (date, *countries, *charts),
    ).fetchone()
    return int(row["cnt"]) if row else 0


def clear_snapshots(
    conn: sqlite3.Connection,
    date: str,
    countries: list[str],
    charts: list[str],
) -> None:
    """Remove snapshots for a date before a fresh fetch to avoid stale data."""
    placeholders_countries = ",".join("?" for _ in countries)
    placeholders_charts = ",".join("?" for _ in charts)
    with conn:
        conn.execute(
            f"""
            DELETE FROM snapshots
            WHERE date = ? AND country IN ({placeholders_countries}) AND chart_type IN ({placeholders_charts})
            """,
            (date, *countries, *charts),
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


def clear_play_snapshots(
    conn: sqlite3.Connection,
    date: str,
    countries: list[str],
    charts: list[str],
) -> None:
    """Remove Google Play snapshots for a date before a fresh fetch."""
    placeholders_countries = ",".join("?" for _ in countries)
    placeholders_charts = ",".join("?" for _ in charts)
    with conn:
        conn.execute(
            f"""
            DELETE FROM play_snapshots
            WHERE date = ? AND country IN ({placeholders_countries}) AND chart_type IN ({placeholders_charts})
            """,
            (date, *countries, *charts),
        )


def replace_play_snapshot(
    conn: sqlite3.Connection,
    date: str,
    region: str,
    country: str,
    chart_type: str,
    category_id: str,
    category_name: str,
    rows: list[dict],
    fetched_at: str,
) -> None:
    """Replace one Google Play chart/category snapshot in a single transaction."""
    with conn:
        for row in rows:
            conn.execute(
                """
                INSERT INTO play_apps (package_name, name, developer, icon_url, first_seen)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(package_name) DO NOTHING
                """,
                (
                    row["app_id"],
                    row.get("name"),
                    row.get("developer"),
                    row.get("icon_url"),
                    date,
                ),
            )

        conn.execute(
            """
            INSERT INTO play_snapshots (date, region, country, chart_type, category_id, category_name, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, region, country, chart_type, category_id)
            DO UPDATE SET category_name = excluded.category_name, fetched_at = excluded.fetched_at
            """,
            (date, region, country, chart_type, category_id, category_name, fetched_at),
        )
        snapshot_id = conn.execute(
            """
            SELECT id FROM play_snapshots
            WHERE date = ? AND region = ? AND country = ? AND chart_type = ? AND category_id = ?
            """,
            (date, region, country, chart_type, category_id),
        ).fetchone()["id"]

        conn.execute("DELETE FROM play_rankings WHERE snapshot_id = ?", (snapshot_id,))
        conn.executemany(
            """
            INSERT INTO play_rankings
                (snapshot_id, rank_no, package_name, name, developer, price_amount, currency, rating, rating_count)
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


def list_dates(conn: sqlite3.Connection, store: str = "app_store") -> list[str]:
    table = "snapshots" if store == "app_store" else "play_snapshots"
    rows = conn.execute(f"SELECT DISTINCT date FROM {table} ORDER BY date").fetchall()
    return [row["date"] for row in rows]


def get_previous_date(conn: sqlite3.Connection, date: str, store: str = "app_store") -> str | None:
    table = "snapshots" if store == "app_store" else "play_snapshots"
    row = conn.execute(
        f"SELECT MAX(date) AS d FROM {table} WHERE date < ?", (date,)
    ).fetchone()
    return row["d"] if row and row["d"] else None


def snapshot_counts(conn: sqlite3.Connection, date: str, store: str = "app_store") -> dict:
    if store == "app_store":
        snapshot_table, ranking_table, snapshot_col = "snapshots", "rankings", "snapshot_id"
    else:
        snapshot_table, ranking_table, snapshot_col = "play_snapshots", "play_rankings", "snapshot_id"
    snapshot_count = conn.execute(
        f"SELECT COUNT(*) AS n FROM {snapshot_table} WHERE date = ?", (date,)
    ).fetchone()["n"]
    entry_count = conn.execute(
        f"""
        SELECT COUNT(*) AS n
        FROM {ranking_table} r JOIN {snapshot_table} s ON s.id = r.{snapshot_col}
        WHERE s.date = ?
        """,
        (date,),
    ).fetchone()["n"]
    country_count = conn.execute(
        f"SELECT COUNT(DISTINCT country) AS n FROM {snapshot_table} WHERE date = ?", (date,)
    ).fetchone()["n"]
    return {
        "snapshots": snapshot_count,
        "entries": entry_count,
        "countries": country_count,
    }
