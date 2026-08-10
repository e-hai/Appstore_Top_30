"""Local interactive dashboard for browsing App Store Top 30 data."""

import json
import socketserver
import sqlite3
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import analyze, config, db

STATIC_DIR = Path(__file__).resolve().parent / "static"


class DashboardServer(ThreadingHTTPServer):
    """HTTP server that avoids reverse-DNS lookups during startup."""

    allow_reuse_address = True

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port


def _query_rankings(
    conn: sqlite3.Connection,
    date: str,
    country: str,
    chart_type: str,
    genre_id: str | None = None,
    store: str = "app_store",
) -> list[dict]:
    if store == "play":
        sql = """
            SELECT r.rank_no, r.package_name AS app_id, r.name, r.developer, r.price_amount,
                   r.currency, r.rating, r.rating_count,
                   s.category_id AS genre_id, s.category_name AS genre_name, a.icon_url
            FROM play_rankings r
            JOIN play_snapshots s ON s.id = r.snapshot_id
            LEFT JOIN play_apps a ON a.package_name = r.package_name
            WHERE s.date = ? AND s.country = ? AND s.chart_type = ?
        """
    else:
        sql = """
            SELECT r.rank_no, r.app_id, r.name, r.developer, r.price_amount,
                   r.currency, r.rating, r.rating_count,
                   s.genre_id, s.genre_name, a.icon_url
            FROM rankings r
            JOIN snapshots s ON s.id = r.snapshot_id
            LEFT JOIN apps a ON a.app_id = r.app_id
            WHERE s.date = ? AND s.country = ? AND s.chart_type = ?
        """
    params: list = [date, country, chart_type]
    if genre_id:
        column = "s.category_id" if store == "play" else "s.genre_id"
        sql += f" AND {column} = ?"
        params.append(genre_id)
    order_column = "s.category_id" if store == "play" else "s.genre_id"
    sql += f" ORDER BY {order_column}, r.rank_no"
    rows = conn.execute(sql, params).fetchall()
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


class DashboardHandler(BaseHTTPRequestHandler):
    db_path = config.DB_PATH

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            if path == "/":
                self._send_file(STATIC_DIR / "dashboard.html", "text/html; charset=utf-8")
            elif path.startswith("/static/"):
                self._send_static(path[len("/static/") :])
            elif path.startswith("/api/"):
                self._handle_api(path, parsed.query)
            else:
                self._send_json({"error": "not found"}, status=404)
        except BrokenPipeError:
            pass
        except Exception as exc:  # noqa: BLE001 - return a readable 500 to the browser
            self._send_json({"error": str(exc)}, status=500)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return

    def _send_static(self, name: str) -> None:
        target = (STATIC_DIR / name).resolve()
        if not target.is_relative_to(STATIC_DIR.resolve()) or not target.is_file():
            self._send_json({"error": "not found"}, status=404)
            return
        content_type = {
            ".css": "text/css; charset=utf-8",
            ".html": "text/html; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
        }.get(target.suffix, "application/octet-stream")
        self._send_file(target, content_type)

    def _send_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _param(self, query: str, key: str) -> str | None:
        values = urllib.parse.parse_qs(query).get(key)
        return values[0] if values else None

    def _handle_api(self, path: str, query: str) -> None:
        conn = db.connect(self.db_path)
        try:
            if path == "/api/dates":
                self._api_dates(conn)
            elif path == "/api/meta":
                self._api_meta(conn, self._param(query, "date"), self._param(query, "store") or "app_store")
            elif path == "/api/rankings":
                self._api_rankings(conn, query)
            elif path == "/api/summary":
                self._api_summary(conn, self._param(query, "date"), self._param(query, "store") or "app_store")
            elif path == "/api/trend":
                self._api_trend(conn, query)
            elif path == "/api/publisher":
                self._api_publisher(conn, query)
            elif path == "/api/category-trends":
                self._api_category_trends(conn, self._param(query, "date"), self._param(query, "store") or "app_store")
            else:
                self._send_json({"error": "unknown api"}, status=404)
        finally:
            conn.close()

    def _api_category_trends(self, conn: sqlite3.Connection, date: str | None, store: str = "app_store") -> None:
        from . import category_intel
        if not date:
            date = db.get_latest_date(conn, store=store) or "2026-08-10"
        res = category_intel.analyze_category_trends(conn, date, store=store)
        self._send_json(res)

    def _api_dates(self, conn: sqlite3.Connection) -> None:
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
        self._send_json(
            {
                "dates": list(grouped.values())
            }
        )

    def _api_meta(self, conn: sqlite3.Connection, date: str | None, store: str) -> None:
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
        self._send_json(
            {
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
        )

    def _api_rankings(self, conn: sqlite3.Connection, query: str) -> None:
        date = self._param(query, "date")
        country = self._param(query, "country")
        chart = self._param(query, "chart")
        store = self._param(query, "store") or "app_store"
        if not date or not country or not chart:
            self._send_json({"error": "date, country, chart are required"}, status=400)
            return
        genre = self._param(query, "genre") or None
        curr_rows = _query_rankings(conn, date, country, chart, genre, store=store)
        prev_date = db.get_previous_date(conn, date, store=store)
        prev_rows = (
            _query_rankings(conn, prev_date, country, chart, genre, store=store)
            if prev_date
            else []
        )
        changes = analyze.compare_rankings(prev_rows, curr_rows)
        quant_res = analyze.enrich_quant_factors(
            conn, changes, country, chart, store=store, genre_id=genre
        )
        attribution = analyze.generate_market_attribution(
            conn, date, country, chart, store=store, genre_id=genre
        )
        self._send_json(
            {
                "date": date,
                "prev_date": prev_date if prev_rows else None,
                "has_previous": bool(prev_rows),
                "country": country,
                "chart": chart,
                "store": store,
                "rows": quant_res["items"],
                "quant_summary": quant_res["summary"],
                "market_attribution": attribution,
            }
        )

    def _api_summary(self, conn: sqlite3.Connection, date: str | None, store: str) -> None:
        if not date:
            self._send_json({"error": "date is required"}, status=400)
            return
        prev_date = db.get_previous_date(conn, date, store=store)
        summaries = analyze.build_all_summaries(conn, date, prev_date, store=store)
        compact_summaries = [
            {key: value for key, value in summary.items() if key != "changes"}
            for summary in summaries
        ]
        self._send_json(
            {
                "date": date,
                "prev_date": prev_date,
                "counts": db.snapshot_counts(conn, date, store=store),
                "store": store,
                "summaries": compact_summaries,
            }
        )

    def _api_trend(self, conn: sqlite3.Connection, query: str) -> None:
        raw_app_ids = self._param(query, "app_ids") or self._param(query, "app_id")
        country = (self._param(query, "country") or "us").lower()
        chart = (self._param(query, "chart") or "free").lower()
        store = (self._param(query, "store") or "app_store").lower()
        genre = self._param(query, "genre")
        if not raw_app_ids:
            self._send_json({"error": "app_id or app_ids is required"}, status=400)
            return
        app_ids = [i.strip() for i in raw_app_ids.split(",") if i.strip()]

        # 设置默认分类 ID（iOS 默认为 36 总榜，Play 默认为 all 总榜）
        target_genre = genre if genre else ("all" if store == "play" else "36")

        trends = {}
        for app_id in app_ids:
            if store == "play":
                rows = conn.execute(
                    """
                    SELECT s.date,
                           MIN(r.rank_no) AS best_rank,
                           GROUP_CONCAT(DISTINCT s.category_name) AS genres,
                           MAX(r.name) AS name
                    FROM play_rankings r
                    JOIN play_snapshots s ON s.id = r.snapshot_id
                    WHERE LOWER(r.package_name) = LOWER(?)
                      AND LOWER(s.country) = ?
                      AND LOWER(s.chart_type) = ?
                      AND s.category_id = ?
                    GROUP BY s.date
                    ORDER BY s.date
                    """,
                    (app_id, country, chart, target_genre),
                ).fetchall()
                if not rows:
                    rows = conn.execute(
                        """
                        SELECT s.date,
                               MIN(r.rank_no) AS best_rank,
                               GROUP_CONCAT(DISTINCT s.category_name) AS genres,
                               MAX(r.name) AS name
                        FROM play_rankings r
                        JOIN play_snapshots s ON s.id = r.snapshot_id
                        WHERE LOWER(r.package_name) = LOWER(?)
                          AND LOWER(s.country) = ?
                          AND LOWER(s.chart_type) = ?
                        GROUP BY s.date
                        ORDER BY s.date
                        """,
                        (app_id, country, chart),
                    ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT s.date,
                           MIN(r.rank_no) AS best_rank,
                           GROUP_CONCAT(DISTINCT s.genre_name) AS genres,
                           MAX(r.name) AS name
                    FROM rankings r
                    JOIN snapshots s ON s.id = r.snapshot_id
                    WHERE (CAST(r.app_id AS TEXT) = ? OR r.app_id = ?)
                      AND LOWER(s.country) = ?
                      AND LOWER(s.chart_type) = ?
                      AND s.genre_id = ?
                    GROUP BY s.date
                    ORDER BY s.date
                    """,
                    (app_id, app_id, country, chart, target_genre),
                ).fetchall()
                if not rows:
                    rows = conn.execute(
                        """
                        SELECT s.date,
                               MIN(r.rank_no) AS best_rank,
                               GROUP_CONCAT(DISTINCT s.genre_name) AS genres,
                               MAX(r.name) AS name
                        FROM rankings r
                        JOIN snapshots s ON s.id = r.snapshot_id
                        WHERE (CAST(r.app_id AS TEXT) = ? OR r.app_id = ?)
                          AND LOWER(s.country) = ?
                          AND LOWER(s.chart_type) = ?
                        GROUP BY s.date
                        ORDER BY s.date
                        """,
                        (app_id, app_id, country, chart),
                    ).fetchall()
            trends[str(app_id)] = [dict(row) for row in rows]
        self._send_json({
            "app_ids": app_ids,
            "store": store,
            "country": country,
            "chart": chart,
            "trends": trends
        })

    def _api_publisher(self, conn: sqlite3.Connection, query: str) -> None:
        developer = self._param(query, "developer")
        date = self._param(query, "date")
        store = self._param(query, "store") or "app_store"
        if not developer or not date:
            self._send_json({"error": "developer and date are required"}, status=400)
            return
        if store == "play":
            rows = conn.execute(
                """
                SELECT DISTINCT r.package_name AS app_id, r.name, r.rank_no,
                                s.country, s.chart_type, s.category_name AS genre_name, a.icon_url
                FROM play_rankings r
                JOIN play_snapshots s ON s.id = r.snapshot_id
                LEFT JOIN play_apps a ON a.package_name = r.package_name
                WHERE r.developer = ? AND s.date = ?
                ORDER BY r.name, s.country, r.rank_no
                """,
                (developer, date),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT DISTINCT r.app_id, r.name, r.rank_no,
                                s.country, s.chart_type, s.genre_name, a.icon_url
                FROM rankings r
                JOIN snapshots s ON s.id = r.snapshot_id
                LEFT JOIN apps a ON a.app_id = r.app_id
                WHERE r.developer = ? AND s.date = ?
                ORDER BY r.name, s.country, r.rank_no
                """,
                (developer, date),
            ).fetchall()
        apps_map = {}
        for row in rows:
            aid = str(row["app_id"])
            if aid not in apps_map:
                apps_map[aid] = {
                    "app_id": aid,
                    "name": row["name"],
                    "icon_url": row["icon_url"],
                    "entries": []
                }
            apps_map[aid]["entries"].append({
                "country": row["country"],
                "chart": row["chart_type"],
                "genre": (
                    config.play_category_display_name(row["genre_name"])
                    if store == "play"
                    else config.genre_display_name(row["genre_name"])
                ),
                "rank": row["rank_no"]
            })
        self._send_json({
            "developer": developer,
            "date": date,
            "store": store,
            "apps": list(apps_map.values())
        })


def start_dashboard(
    db_path: Path = config.DB_PATH,
    host: str = "0.0.0.0",
    port: int = 8000,
    open_browser: bool = True,
) -> DashboardServer:
    db.init_db(db_path)
    DashboardHandler.db_path = db_path
    server = DashboardServer((host, port), DashboardHandler)
    display_host = "127.0.0.1" if host == "0.0.0.0" else host
    url = f"http://{display_host}:{port}"
    print(f"App Store Top 30 dashboard running at {url}", flush=True)
    if open_browser:
        webbrowser.open(url)
    return server
