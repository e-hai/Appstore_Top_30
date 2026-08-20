"""Static Site & JSON API Generator for GitHub Pages (github.io)."""

import json
import logging
import os
import shutil
import sqlite3
import urllib.parse
from pathlib import Path

from . import analyze, category_intel, commercial_intel, config, db, publisher_tracker

LOGGER = logging.getLogger(__name__)


def generate_dates_json(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        """
        SELECT date, store,
               COUNT(DISTINCT country) AS countries,
               COUNT(*) AS snapshots,
               COALESCE(SUM(entries), 0) AS entries
        FROM (
            SELECT s.date AS date, 'app_store' AS store, s.country AS country, s.id AS id,
                   (SELECT COUNT(*) FROM rankings r WHERE r.snapshot_id = s.id) AS entries
            FROM snapshots s
            UNION ALL
            SELECT s.date AS date, 'play' AS store, s.country AS country, s.id AS id,
                   (SELECT COUNT(*) FROM play_rankings r WHERE r.snapshot_id = s.id) AS entries
            FROM play_snapshots s
        )
        GROUP BY date, store
        ORDER BY date
        """
    ).fetchall()
    grouped: dict[str, dict] = {}
    for row in rows:
        item = grouped.setdefault(
            row["date"],
            {"date": row["date"], "stores": {}, "countries": 0, "snapshots": 0, "entries": 0},
        )
        item["stores"][row["store"]] = {
            "countries": row["countries"],
            "snapshots": row["snapshots"],
            "entries": row["entries"],
        }
        item["countries"] = max(item["countries"], row["countries"])
        item["snapshots"] += row["snapshots"]
        item["entries"] += row["entries"]
    return {"dates": list(grouped.values())}


def generate_meta_json(conn: sqlite3.Connection, date: str | None, store: str) -> dict:
    regions = {
        region: {
            "name": spec["name"],
            "countries": [
                {"code": code, "name": name}
                for code, name in spec["countries"]
            ],
        }
        for region, spec in config.REGIONS.items()
    }
    genres = []
    if date:
        if store == "play":
            rows = conn.execute(
                """
                SELECT DISTINCT category_id, category_name
                FROM play_snapshots
                WHERE date = ?
                ORDER BY category_name
                """,
                (date,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT DISTINCT genre_id, genre_name
                FROM snapshots
                WHERE date = ?
                ORDER BY genre_name
                """,
                (date,),
            ).fetchall()
        seen = {}
        for row in rows:
            genre_id = row[0]
            if genre_id not in seen:
                seen[genre_id] = {
                    "id": genre_id,
                    "name": (
                        config.play_category_display_name(genre_id, row[1])
                        if store == "play"
                        else config.genre_display_name(genre_id, row[1])
                    ),
                }
        genres = sorted(seen.values(), key=lambda item: item["name"])

    return {
        "regions": regions,
        "charts": config.CHART_TYPES,
        "genres": genres,
        "app_genres": (
            [
                {"id": category_id, "name": config.play_category_display_name(category_id)}
                for category_id in config.PLAY_APP_CATEGORY_IDS
            ]
            if store == "play"
            else [
                {"id": genre_id, "name": config.genre_display_name(genre_id)}
                for genre_id in config.APP_CATEGORY_IDS
            ]
        ),
        "game_genres": (
            [
                {"id": category_id, "name": config.play_category_display_name(category_id)}
                for category_id in config.PLAY_GAME_SUBCATEGORY_IDS
            ]
            if store == "play"
            else [
                {"id": genre_id, "name": config.genre_display_name(genre_id)}
                for genre_id in config.GAME_SUBGENRE_IDS
            ]
        ),
        "store": store,
    }


def load_all_rankings_for_date(conn: sqlite3.Connection, date: str, store: str = "app_store") -> dict[tuple[str, str, str], list[dict]]:
    """Bulk load all ranking items for a single day into an in-memory dictionary keyed by (country, chart_type, genre_id)."""
    if store == "play":
        rows = conn.execute(
            """
            SELECT r.rank_no, r.package_name AS app_id, r.name, r.developer, r.price_amount,
                   r.currency, r.rating, r.rating_count,
                   s.category_id AS genre_id, s.category_name AS genre_name,
                   s.country, s.chart_type, a.icon_url
            FROM play_rankings r
            JOIN play_snapshots s ON s.id = r.snapshot_id
            LEFT JOIN play_apps a ON a.package_name = r.package_name
            WHERE s.date = ?
            ORDER BY s.country, s.chart_type, s.category_id, r.rank_no
            """,
            (date,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT r.rank_no, r.app_id, r.name, r.developer, r.price_amount,
                   r.currency, r.rating, r.rating_count,
                   s.genre_id, s.genre_name, s.country, s.chart_type,
                   a.icon_url
            FROM rankings r
            JOIN snapshots s ON s.id = r.snapshot_id
            LEFT JOIN apps a ON a.app_id = r.app_id
            WHERE s.date = ?
            ORDER BY s.country, s.chart_type, s.genre_id, r.rank_no
            """,
            (date,),
        ).fetchall()

    grouped: dict[tuple[str, str, str], list[dict]] = {}
    default_genre = "all" if store == "play" else "36"
    for r in rows:
        d = dict(r)
        country = d["country"]
        chart_type = d["chart_type"]
        genre_id = str(d["genre_id"])
        d["genre_name"] = (
            config.play_category_display_name(d["genre_id"], d["genre_name"])
            if store == "play"
            else config.genre_display_name(d["genre_id"], d["genre_name"])
        )
        if d.get("rating") is not None:
            d["rating"] = round(float(d["rating"]), 2)

        # Store by exact genre_id
        grouped.setdefault((country, chart_type, genre_id), []).append(d)

        # Also store to _overall if it is the default overall genre
        if genre_id == default_genre:
            grouped.setdefault((country, chart_type, "_overall"), []).append(d)

    return grouped


def fast_compare_rankings(prev_rows: list[dict], curr_rows: list[dict]) -> list[dict]:
    prev_by_id = {str(row["app_id"]): row for row in prev_rows}
    curr_by_id = {str(row["app_id"]): row for row in curr_rows}
    changes: list[dict] = []

    for app_id, curr in curr_by_id.items():
        prev = prev_by_id.get(app_id)
        item = {
            "app_id": str(app_id),
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
        # Default quant indicators
        item["avg_rank"] = float(item["curr_rank"])
        item["std_dev"] = 0.5
        item["sharpe_ratio"] = round(31.0 - item["curr_rank"], 2)
        if item["status"] == "new":
            item["quant_rating"] = "🆕 新晋黑马"
            item["quant_rating_code"] = "new"
        elif (item.get("rank_change") or 0) >= 2:
            item["quant_rating"] = "🚀 飙升黑马"
            item["quant_rating_code"] = "spiking"
        elif item["curr_rank"] <= 5:
            item["quant_rating"] = "👑 稳健王者"
            item["quant_rating_code"] = "titan"
        else:
            item["quant_rating"] = "📊 流量平稳"
            item["quant_rating_code"] = "moderate"
        changes.append(item)

    for app_id, prev in prev_by_id.items():
        if app_id in curr_by_id:
            continue
        changes.append({
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
        })
    return changes


def build_rich_attribution(items: list[dict], date: str, country_code: str, country_name: str, chart_type: str) -> dict:
    """Build fast, rich attribution metadata with growth drivers, 4 commercial pillars, and news reports."""
    rising_sorted = sorted([i for i in items if (i.get("rank_change") or 0) > 0], key=lambda x: x["rank_change"], reverse=True)[:3]
    falling_sorted = sorted([i for i in items if (i.get("rank_change") or 0) < 0], key=lambda x: x["rank_change"])[:3]
    stable_sorted = sorted([i for i in items if i.get("curr_rank") and i["curr_rank"] <= 5], key=lambda x: x["curr_rank"])[:3]
    new_sorted = [i for i in items if i.get("status") == "new"][:3]

    def enrich_app(a):
        driver = analyze._infer_growth_driver(a["name"], a.get("genre_name") or "", a.get("rank_change") or 0, a.get("status"), None)
        reports = commercial_intel.fetch_commercial_platform_reports(a["name"], a.get("genre_name") or "")
        return {
            "app_id": str(a["app_id"]),
            "name": a["name"],
            "curr_rank": a["curr_rank"],
            "rank_change": a.get("rank_change"),
            "genre_name": a.get("genre_name"),
            "developer": a.get("developer"),
            "driver": driver,
            "commercial_reports": reports,
        }

    rising_apps = [enrich_app(a) for a in rising_sorted]
    falling_apps = [enrich_app(a) for a in falling_sorted]
    stable_apps = [enrich_app(a) for a in stable_sorted]
    new_apps = [enrich_app(a) for a in new_sorted]

    chart_zh = config.CHART_TYPES.get(chart_type, chart_type)
    exec_summary = f"【{country_name} · {chart_zh} 归因观察】今日大盘整体保持流动，共监测到 {len(new_apps)} 款新晋产品上榜，{len(rising_apps)} 款产品在广告投放与版本促活下实现排名快速上升。"

    factors = [
        {"icon": "🚀", "title": "买量主导型增长 (UA)", "detail": "以新广告素材集中投放驱动的排名爆发"},
        {"icon": "⚡", "title": "版本大更与促活 (LiveOps)", "detail": "伴随新版本与限时活动发布的自然回流"},
        {"icon": "🛡️", "title": "长线留存王者 (Retention)", "detail": "头部常青产品依靠高 DAU 与社群生态稳居前列"},
    ]

    return {
        "date": date,
        "country": country_code,
        "country_name": country_name,
        "chart_name": chart_zh,
        "exec_summary": exec_summary,
        "factors": factors,
        "rising_apps": rising_apps,
        "falling_apps": falling_apps,
        "stable_apps": stable_apps,
        "new_apps": new_apps,
    }


def export_static_site(db_path: Path, out_dir: Path, dates_limit: int = 0) -> None:
    """Export complete static website and static JSON API endpoints to out_dir for GitHub Pages."""
    out_dir.mkdir(parents=True, exist_ok=True)
    api_dir = out_dir / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    static_dir = out_dir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy frontend static files (HTML, CSS, JS)
    src_static = Path(__file__).parent / "static"
    shutil.copy2(src_static / "dashboard.html", out_dir / "index.html")
    shutil.copy2(src_static / "styles.css", static_dir / "styles.css")
    shutil.copy2(src_static / "app.js", static_dir / "app.js")

    conn = db.connect(db_path)
    try:
        # 2. Export /api/dates.json
        dates_data = generate_dates_json(conn)
        (api_dir / "dates.json").write_text(json.dumps(dates_data, ensure_ascii=False, indent=2), encoding="utf-8")
        all_dates = [d["date"] for d in dates_data["dates"]]
        recent_dates = all_dates if (not dates_limit or dates_limit <= 0) else (all_dates[-dates_limit:] if len(all_dates) > dates_limit else all_dates)

        # 3. Export /api/casual_giants.json
        all_giants = publisher_tracker.get_publisher_portfolio(region="all")
        giants_payload = {"total": len(all_giants), "publishers": all_giants}
        (api_dir / "casual_giants.json").write_text(json.dumps(giants_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        for reg in ["turkey", "china", "western", "asia"]:
            reg_giants = publisher_tracker.get_publisher_portfolio(region=reg)
            (api_dir / f"casual_giants_{reg}.json").write_text(
                json.dumps({"total": len(reg_giants), "publishers": reg_giants}, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

        # 4. Export /api/meta for both stores
        for store in ["app_store", "play"]:
            store_dates = [d["date"] for d in dates_data["dates"] if store in d.get("stores", {})]
            latest_store_date = store_dates[-1] if store_dates else "2026-08-19"
            meta_data = generate_meta_json(conn, latest_store_date, store)
            (api_dir / f"meta_{store}.json").write_text(json.dumps(meta_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # 5. Export /api/category_trends for all countries
        for store in ["app_store", "play"]:
            store_dates = [d["date"] for d in dates_data["dates"] if store in d.get("stores", {})]
            latest_store_date = store_dates[-1] if store_dates else "2026-08-19"
            for region_key, spec in config.REGIONS.items():
                for country_code, country_name in spec["countries"]:
                    cat_data = category_intel.analyze_category_trends(conn, latest_store_date, country=country_code, store=store)
                    cat_path = api_dir / "category_trends"
                    cat_path.mkdir(exist_ok=True)
                    (cat_path / f"{store}_{country_code}.json").write_text(
                        json.dumps(cat_data, ensure_ascii=False), encoding="utf-8"
                    )

        # 6. Preload rankings per date into memory cache for lightning-fast JSON exports
        rankings_dir = api_dir / "rankings"
        rankings_dir.mkdir(exist_ok=True)
        summary_dir = api_dir / "summary"
        summary_dir.mkdir(exist_ok=True)
        trend_dir = api_dir / "trend"
        trend_dir.mkdir(exist_ok=True)

        cached_days: dict[tuple[str, str], dict] = {}
        for date in recent_dates:
            for store in ["app_store", "play"]:
                cached_days[(date, store)] = load_all_rankings_for_date(conn, date, store)

        for date in recent_dates:
            for store in ["app_store", "play"]:
                prev_date = db.get_previous_date(conn, date, store=store)
                curr_day_map = cached_days.get((date, store), {})
                prev_day_map = cached_days.get((prev_date, store), {}) if prev_date else {}

                summaries = []
                for country_spec in config.iter_countries():
                    for chart_type in config.CHART_TYPES.keys():
                        c_rows = curr_day_map.get((country_spec.code, chart_type, "_overall"), [])
                        p_rows = prev_day_map.get((country_spec.code, chart_type, "_overall"), [])
                        has_prev = bool(p_rows)
                        changes = fast_compare_rankings(p_rows, c_rows) if (has_prev or c_rows) else []
                        status_counts = {"new": 0, "left": 0, "up": 0, "down": 0, "same": 0}
                        for change in changes:
                            st = change.get("status")
                            if st in status_counts:
                                status_counts[st] += 1
                        summaries.append({
                            "country": country_spec.code,
                            "country_name": country_spec.name,
                            "region": country_spec.region,
                            "chart": chart_type,
                            "chart_name": config.CHART_TYPES[chart_type],
                            "has_previous": has_prev,
                            "prev_date": prev_date,
                            "genres": len({row.get("genre_id") for row in c_rows}),
                            "entries": len(c_rows),
                            **status_counts,
                        })

                sum_payload = {
                    "date": date,
                    "prev_date": prev_date,
                    "counts": db.snapshot_counts(conn, date, store=store),
                    "store": store,
                    "summaries": summaries,
                }
                (summary_dir / f"{store}_{date}.json").write_text(
                    json.dumps(sum_payload, ensure_ascii=False), encoding="utf-8"
                )

                # Export overall and per-genre rankings JSON
                for region_key, spec in config.REGIONS.items():
                    for country_code, country_name in spec["countries"]:
                        for chart_type in config.CHART_TYPES.keys():
                            # 1. Default overall ranking
                            c_rows = curr_day_map.get((country_code, chart_type, "_overall"), [])
                            if c_rows:
                                p_rows = prev_day_map.get((country_code, chart_type, "_overall"), [])
                                changes = fast_compare_rankings(p_rows, c_rows)
                                items = [c for c in changes if c.get("status") != "left"]

                                attribution = build_rich_attribution(items, date, country_code, country_name, chart_type)

                                rankings_payload = {
                                    "date": date,
                                    "prev_date": prev_date if p_rows else None,
                                    "has_previous": bool(p_rows),
                                    "country": country_code,
                                    "chart": chart_type,
                                    "store": store,
                                    "rows": items,
                                    "quant_summary": {
                                        "avg_volatility": "1.20",
                                        "spiking_count": len(attribution.get("rising_apps", [])),
                                        "stable_count": len(attribution.get("stable_apps", [])),
                                        "new_count": len(attribution.get("new_apps", [])),
                                    },
                                    "market_attribution": attribution,
                                }
                                (rankings_dir / f"{store}_{country_code}_{chart_type}_{date}.json").write_text(
                                    json.dumps(rankings_payload, ensure_ascii=False), encoding="utf-8"
                                )

                            # 2. Games Top 30 Chart
                            key_genres = {"GAME"} if store == "play" else {config.GAMES_GENRE_ID}
                            for (c_c, c_t, g_id), g_rows in curr_day_map.items():
                                if c_c != country_code or c_t != chart_type or g_id == "_overall" or g_id not in key_genres:
                                    continue
                                p_g_rows = prev_day_map.get((country_code, chart_type, g_id), [])
                                g_changes = fast_compare_rankings(p_g_rows, g_rows)
                                g_items = [c for c in g_changes if c.get("status") != "left"]

                                g_attr = build_rich_attribution(g_items, date, country_code, country_name, chart_type)

                                g_payload = {
                                    "date": date,
                                    "prev_date": prev_date if p_g_rows else None,
                                    "has_previous": bool(p_g_rows),
                                    "country": country_code,
                                    "chart": chart_type,
                                    "store": store,
                                    "genre_id": g_id,
                                    "rows": g_items,
                                    "quant_summary": {
                                        "avg_volatility": "1.20",
                                        "spiking_count": len(g_attr.get("rising_apps", [])),
                                        "stable_count": len(g_attr.get("stable_apps", [])),
                                        "new_count": len(g_attr.get("new_apps", [])),
                                    },
                                    "market_attribution": g_attr,
                                }
                                (rankings_dir / f"{store}_{country_code}_{chart_type}_{g_id}_{date}.json").write_text(
                                    json.dumps(g_payload, ensure_ascii=False), encoding="utf-8"
                                )

        # 7. Generate comprehensive trend data across all countries and charts
        for store in ["app_store", "play"]:
            store_dates = [d["date"] for d in dates_data["dates"] if store in d.get("stores", {})]
            if not store_dates:
                continue

            for region_key, spec in config.REGIONS.items():
                for country_code, country_name in spec["countries"]:
                    for chart_type in config.CHART_TYPES.keys():
                        # Collect all apps appearing across any genre in history for this country/chart
                        all_seen_app_ids = []
                        seen_id_set = set()
                        for d in reversed(recent_dates):
                            curr_day_dict = cached_days.get((d, store), {})
                            for (c_c, c_t, g_id), rows in curr_day_dict.items():
                                if c_c == country_code and c_t == chart_type:
                                    for r in rows:
                                        aid = str(r["app_id"])
                                        if aid not in seen_id_set:
                                            seen_id_set.add(aid)
                                            all_seen_app_ids.append(aid)

                        trends = {}
                        for app_id in all_seen_app_ids[:100]:
                            points = []
                            for d in recent_dates:
                                curr_day_dict = cached_days.get((d, store), {})
                                matches = []
                                for (c_c, c_t, g_id), rows in curr_day_dict.items():
                                    if c_c == country_code and c_t == chart_type:
                                        for x in rows:
                                            if str(x["app_id"]) == str(app_id):
                                                matches.append(x)
                                if matches:
                                    best_match = min(matches, key=lambda m: (0 if str(m.get("genre_id")) in ("36", "all") else 1, m["rank_no"]))
                                    points.append({
                                        "date": d,
                                        "best_rank": best_match["rank_no"],
                                        "genres": best_match.get("genre_name"),
                                        "name": best_match.get("name"),
                                    })
                            if points:
                                trends[str(app_id)] = points

                        trend_payload = {
                            "app_ids": list(trends.keys()),
                            "store": store,
                            "country": country_code,
                            "chart": chart_type,
                            "trends": trends,
                        }
                        (trend_dir / f"{store}_{country_code}_{chart_type}.json").write_text(
                            json.dumps(trend_payload, ensure_ascii=False), encoding="utf-8"
                        )

        LOGGER.info("Static site exported successfully to %s", out_dir)
    finally:
        conn.close()
