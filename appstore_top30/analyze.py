"""Day-over-day ranking analysis."""

import sqlite3

from . import config


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_rows(
    conn: sqlite3.Connection,
    date: str,
    country: str,
    chart_type: str,
    store: str = "app_store",
) -> list[dict]:
    if store == "play":
        rows = conn.execute(
            """
            SELECT r.rank_no, r.package_name AS app_id, r.name, r.developer, r.price_amount,
                   r.currency, r.rating, r.rating_count,
                   s.category_id AS genre_id, s.category_name AS genre_name,
                   s.country AS country, a.icon_url
            FROM play_rankings r
            JOIN play_snapshots s ON s.id = r.snapshot_id
            LEFT JOIN play_apps a ON a.package_name = r.package_name
            WHERE s.date = ? AND s.country = ? AND s.chart_type = ?
            ORDER BY s.category_id, r.rank_no
            """,
            (date, country, chart_type),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT r.rank_no, r.app_id, r.name, r.developer, r.price_amount,
                   r.currency, r.rating, r.rating_count,
                   s.genre_id, s.genre_name, s.country AS country,
                   a.icon_url
            FROM rankings r
            JOIN snapshots s ON s.id = r.snapshot_id
            LEFT JOIN apps a ON a.app_id = r.app_id
            WHERE s.date = ? AND s.country = ? AND s.chart_type = ?
            ORDER BY s.genre_id, r.rank_no
            """,
            (date, country, chart_type),
        ).fetchall()
    return [
        {
            **dict(row),
            "genre_name": (
                config.play_category_display_name(row["genre_id"], row["genre_name"])
                if store == "play"
                else config.genre_display_name(row["genre_id"], row["genre_name"])
            ),
        }
        for row in rows
    ]


def compare_rankings(prev_rows: list[dict], curr_rows: list[dict]) -> list[dict]:
    prev_by_id = {row["app_id"]: row for row in prev_rows}
    curr_by_id = {row["app_id"]: row for row in curr_rows}
    changes: list[dict] = []

    for app_id, curr in curr_by_id.items():
        prev = prev_by_id.get(app_id)
        item = {
            "app_id": app_id,
            "name": curr.get("name"),
            "developer": curr.get("developer"),
            "icon_url": curr.get("icon_url"),
            "genre_id": curr.get("genre_id"),
            "genre_name": curr.get("genre_name"),
            "curr_rank": curr["rank_no"],
            "prev_rank": prev["rank_no"] if prev else None,
            "price_amount": curr.get("price_amount"),
            "price_currency": curr.get("currency"),
            "prev_price_amount": prev.get("price_amount") if prev else None,
            "rating": curr.get("rating"),
            "prev_rating": prev.get("rating") if prev else None,
            "rating_count": curr.get("rating_count"),
        }
        if prev is None:
            item["status"] = "new"
            item["rank_change"] = None
        else:
            item["rank_change"] = prev["rank_no"] - curr["rank_no"]
            item["status"] = (
                "same" if item["rank_change"] == 0
                else "up" if item["rank_change"] > 0
                else "down"
            )
        item["price_change"] = (
            round(_to_float(curr.get("price_amount")) - _to_float(prev.get("price_amount")), 2)
            if prev is not None
            and _to_float(curr.get("price_amount")) is not None
            and _to_float(prev.get("price_amount")) is not None
            else None
        )
        item["rating_change"] = (
            round(curr.get("rating") - prev.get("rating"), 2)
            if prev is not None
            and curr.get("rating") is not None
            and prev.get("rating") is not None
            else None
        )
        changes.append(item)

    for app_id, prev in prev_by_id.items():
        if app_id in curr_by_id:
            continue
        changes.append(
            {
                "app_id": app_id,
                "name": prev.get("name"),
                "developer": prev.get("developer"),
                "icon_url": prev.get("icon_url"),
                "genre_id": prev.get("genre_id"),
                "genre_name": prev.get("genre_name"),
                "curr_rank": None,
                "prev_rank": prev["rank_no"],
                "price_amount": None,
                "price_currency": prev.get("currency"),
                "prev_price_amount": prev.get("price_amount"),
                "rating": None,
                "prev_rating": prev.get("rating"),
                "rating_count": None,
                "status": "left",
                "rank_change": None,
                "price_change": None,
                "rating_change": None,
            }
        )
    return changes


def build_country_chart_summary(
    conn: sqlite3.Connection,
    date: str,
    prev_date: str | None,
    country: str,
    chart_type: str,
    store: str = "app_store",
) -> dict:
    curr_rows = _load_rows(conn, date, country, chart_type, store=store)
    prev_rows = _load_rows(conn, prev_date, country, chart_type, store=store) if prev_date else []
    has_previous = bool(prev_rows)
    changes = compare_rankings(prev_rows, curr_rows) if has_previous else []

    status_counts = {status: 0 for status in ("new", "left", "up", "down", "same")}
    for change in changes:
        if change["status"] in status_counts:
            status_counts[change["status"]] += 1

    country_spec = next(
        (c for c in config.iter_countries() if c.code == country),
        config.Country(code=country, name=country.upper(), region=""),
    )
    return {
        "country": country,
        "country_name": country_spec.name,
        "region": country_spec.region,
        "chart": chart_type,
        "chart_name": config.CHART_TYPES[chart_type],
        "has_previous": has_previous,
        "prev_date": prev_date,
        "genres": len({row["genre_id"] for row in curr_rows}),
        "entries": len(curr_rows),
        **status_counts,
        "changes": changes,
    }


def build_all_summaries(
    conn: sqlite3.Connection,
    date: str,
    prev_date: str | None,
    store: str = "app_store",
) -> list[dict]:
    summaries = []
    for country in config.iter_countries():
        for chart_type in config.CHART_TYPES:
            summaries.append(
                build_country_chart_summary(
                    conn,
                    date,
                    prev_date,
                    country.code,
                    chart_type,
                    store,
                )
            )
    return summaries


def top_new_entries(changes: list[dict], limit: int = 20) -> list[dict]:
    return sorted(
        (c for c in changes if c["status"] == "new"),
        key=lambda c: (c["curr_rank"] is None, c["curr_rank"]),
    )[:limit]


def top_left_entries(changes: list[dict], limit: int = 20) -> list[dict]:
    return sorted(
        (c for c in changes if c["status"] == "left"),
        key=lambda c: (c["prev_rank"] is None, c["prev_rank"]),
    )[:limit]


def top_movers(changes: list[dict], limit: int = 20) -> list[dict]:
    with_change = [c for c in changes if c.get("rank_change") is not None]
    return sorted(
        with_change,
        key=lambda c: abs(c["rank_change"]),
        reverse=True,
    )[:limit]


def top_rating_changes(changes: list[dict], limit: int = 20) -> list[dict]:
    with_change = [c for c in changes if c.get("rating_change") is not None and c["rating_change"] != 0]
    return sorted(with_change, key=lambda c: abs(c["rating_change"]), reverse=True)[:limit]
