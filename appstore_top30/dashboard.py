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
) -> list[dict]:
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
        sql += " AND s.genre_id = ?"
        params.append(genre_id)
    sql += " ORDER BY s.genre_id, r.rank_no"
    rows = conn.execute(sql, params).fetchall()
    return [
        {
            **dict(row),
            "genre_name": config.genre_display_name(row["genre_id"], row["genre_name"]),
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
                self._api_meta(conn, self._param(query, "date"))
            elif path == "/api/rankings":
                self._api_rankings(conn, query)
            elif path == "/api/summary":
                self._api_summary(conn, self._param(query, "date"))
            elif path == "/api/trend":
                self._api_trend(conn, query)
            else:
                self._send_json({"error": "unknown api"}, status=404)
        finally:
            conn.close()

    def _api_dates(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute(
            """
            SELECT s.date,
                   COUNT(DISTINCT s.country) AS countries,
                   COUNT(*) AS snapshots,
                   COALESCE(SUM((SELECT COUNT(*) FROM rankings r WHERE r.snapshot_id = s.id)), 0) AS entries
            FROM snapshots s
            GROUP BY s.date
            ORDER BY s.date
            """
        ).fetchall()
        self._send_json(
            {
                "dates": [
                    {
                        "date": row["date"],
                        "countries": row["countries"],
                        "snapshots": row["snapshots"],
                        "entries": row["entries"],
                    }
                    for row in rows
                ]
            }
        )

    def _api_meta(self, conn: sqlite3.Connection, date: str | None) -> None:
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
                genre_id = row["genre_id"]
                if genre_id not in seen:
                    seen[genre_id] = {
                        "genre_id": genre_id,
                        "genre_name": config.genre_display_name(genre_id, row["genre_name"]),
                    }
            genres = sorted(seen.values(), key=lambda item: item["genre_name"])
        self._send_json(
            {
                "regions": regions,
                "charts": config.CHART_TYPES,
                "genres": genres,
                "app_genres": [
                    {"id": genre_id, "name": config.genre_display_name(genre_id)}
                    for genre_id in config.APP_CATEGORY_IDS
                ],
                "game_genres": [
                    {"id": genre_id, "name": config.genre_display_name(genre_id)}
                    for genre_id in config.GAME_SUBGENRE_IDS
                ],
            }
        )

    def _api_rankings(self, conn: sqlite3.Connection, query: str) -> None:
        date = self._param(query, "date")
        country = self._param(query, "country")
        chart = self._param(query, "chart")
        if not date or not country or not chart:
            self._send_json({"error": "date, country, chart are required"}, status=400)
            return
        genre = self._param(query, "genre") or None
        curr_rows = _query_rankings(conn, date, country, chart, genre)
        prev_date = db.get_previous_date(conn, date)
        prev_rows = (
            _query_rankings(conn, prev_date, country, chart, genre)
            if prev_date
            else []
        )
        changes = analyze.compare_rankings(prev_rows, curr_rows)
        self._send_json(
            {
                "date": date,
                "prev_date": prev_date if prev_rows else None,
                "has_previous": bool(prev_rows),
                "country": country,
                "chart": chart,
                "rows": changes,
            }
        )

    def _api_summary(self, conn: sqlite3.Connection, date: str | None) -> None:
        if not date:
            self._send_json({"error": "date is required"}, status=400)
            return
        prev_date = db.get_previous_date(conn, date)
        summaries = analyze.build_all_summaries(conn, date, prev_date)
        compact_summaries = [
            {key: value for key, value in summary.items() if key != "changes"}
            for summary in summaries
        ]
        self._send_json(
            {
                "date": date,
                "prev_date": prev_date,
                "counts": db.snapshot_counts(conn, date),
                "summaries": compact_summaries,
            }
        )

    def _api_trend(self, conn: sqlite3.Connection, query: str) -> None:
        app_id = self._param(query, "app_id")
        country = self._param(query, "country")
        chart = self._param(query, "chart")
        if not app_id or not country or not chart:
            self._send_json({"error": "app_id, country, chart are required"}, status=400)
            return
        rows = conn.execute(
            """
            SELECT s.date,
                   MIN(r.rank_no) AS best_rank,
                   GROUP_CONCAT(DISTINCT s.genre_name) AS genres,
                   MAX(r.name) AS name
            FROM rankings r
            JOIN snapshots s ON s.id = r.snapshot_id
            WHERE r.app_id = ? AND s.country = ? AND s.chart_type = ?
            GROUP BY s.date
            ORDER BY s.date
            """,
            (app_id, country, chart),
        ).fetchall()
        self._send_json({"app_id": app_id, "rows": [dict(row) for row in rows]})


def start_dashboard(
    db_path: Path = config.DB_PATH,
    host: str = "127.0.0.1",
    port: int = 8000,
    open_browser: bool = True,
) -> DashboardServer:
    db.init_db(db_path)
    DashboardHandler.db_path = db_path
    server = DashboardServer((host, port), DashboardHandler)
    url = f"http://{host}:{port}"
    print(f"App Store Top 30 dashboard running at {url}", flush=True)
    if open_browser:
        webbrowser.open(url)
    return server
