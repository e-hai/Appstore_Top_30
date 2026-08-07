"""Fetch App Store rankings from Apple's public charts and lookup APIs."""

import json
import logging
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from . import config, db

LOGGER = logging.getLogger(__name__)

FEED_PATHS = {
    "free": "topfreeapplications",
    "paid": "toppaidapplications",
    "grossing": "topgrossingapplications",
}

CHART_NAMES = {
    "free": "FreeApplications",
    "paid": "PaidApplications",
    "grossing": "AppsByRevenue",
}

USER_AGENT = "AppStoreTop30Analyzer/0.1 (+daily ranking analysis)"


class RateLimiter:
    """Small global rate limiter shared by all Apple API requests."""

    def __init__(self, requests_per_second: float = config.REQUESTS_PER_SECOND) -> None:
        self._interval = 1.0 / requests_per_second
        self._lock = threading.Lock()
        self._next_at = time.monotonic()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait_for = self._next_at - now
            if wait_for > 0:
                time.sleep(wait_for)
            self._next_at = max(now, self._next_at) + self._interval


RATE_LIMITER = RateLimiter()


class FetchError(RuntimeError):
    pass


def _backoff_seconds(attempt: int, exc: Exception) -> float:
    if isinstance(exc, urllib.error.HTTPError) and exc.code in {403, 429, 500, 502, 503, 504}:
        seconds = float(2 ** (attempt + 1))
    else:
        seconds = 0.5 * (2 ** attempt)
    return seconds + random.uniform(0, 0.4)


def _http_get_json(url: str, timeout: int = config.FEED_TIMEOUT, retries: int = config.FEED_RETRIES) -> dict:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            RATE_LIMITER.wait()
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(_backoff_seconds(attempt, exc))
    raise FetchError(f"failed to fetch {url}: {last_error}")


def _parse_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value))
    except ValueError:
        return None


def fetch_genre_map(country: str) -> dict:
    """Return the localized App Store genre tree keyed by genre id."""
    url = (
        "https://itunes.apple.com/WebObjects/MZStoreServices.woa/ws/genres"
        f"?id={config.GENRE_ROOT_ID}&cc={country}"
    )
    payload = _http_get_json(url)
    root = payload[config.GENRE_ROOT_ID]

    genre_map = {}

    def walk(node: dict, parent: str | None) -> None:
        genre_id = str(node["id"])
        genre_map[genre_id] = {
            "id": genre_id,
            "name": node["name"],
            "parent": parent,
        }
        for child in node.get("subgenres", {}).values():
            walk(child, genre_id)

    walk(root, None)
    return genre_map


def select_genres(genre_map: dict) -> list[dict]:
    """Select root, top-level categories, and subgenres of Games."""
    root_id = config.GENRE_ROOT_ID
    selected = [{"id": root_id, "name": genre_map[root_id]["name"]}]
    for genre in genre_map.values():
        if genre["parent"] == root_id:
            selected.append({"id": genre["id"], "name": genre["name"]})
    for genre in genre_map.values():
        if genre["parent"] == config.GAMES_GENRE_ID:
            selected.append({"id": genre["id"], "name": genre["name"]})
    return selected


def parse_feed_entry(entry: dict, rank: int) -> dict:
    id_attrs = entry.get("id", {}).get("attributes", {})
    price_attrs = entry.get("im:price", {}).get("attributes", {})
    images = entry.get("im:image", []) or []
    if isinstance(images, dict):
        images = [images]
    icon_url = None
    for image in images:
        if image.get("attributes", {}).get("height") == "100":
            icon_url = image.get("label")
    if icon_url is None and images:
        icon_url = images[-1].get("label")

    return {
        "app_id": int(id_attrs.get("im:id", "0")),
        "bundle_id": id_attrs.get("im:bundleId"),
        "name": entry.get("im:name", {}).get("label"),
        "developer": entry.get("im:artist", {}).get("label"),
        "icon_url": icon_url,
        "price_amount": _parse_float(price_attrs.get("amount")),
        "currency": price_attrs.get("currency"),
        "rank": rank,
    }


def fetch_feed(country: str, chart_type: str, genre_id: str, limit: int = config.TOP_N) -> list[dict]:
    feed_path = FEED_PATHS[chart_type]
    url = (
        f"https://itunes.apple.com/{country}/rss/{feed_path}"
        f"/limit={limit}/genre={genre_id}/json"
    )
    payload = _http_get_json(url)
    entries = payload.get("feed", {}).get("entry", [])
    if isinstance(entries, dict):
        entries = [entries]
    return [parse_feed_entry(entry, index + 1) for index, entry in enumerate(entries)]


def fetch_chart_ids(
    country: str,
    chart_type: str,
    genre_id: str,
    limit: int = config.TOP_N,
) -> list[int]:
    """Fetch ranked app ids from the App Store charts API."""
    url = (
        "https://itunes.apple.com/WebObjects/MZStoreServices.woa/ws/charts"
        f"?cc={country}&g={genre_id}&name={CHART_NAMES[chart_type]}&limit={limit}"
    )
    payload = _http_get_json(url)
    return [int(app_id) for app_id in payload.get("resultIds", []) if str(app_id).isdigit()]


def fetch_ratings(
    country: str,
    app_ids: set[int],
    batch_size: int = config.LOOKUP_BATCH_SIZE,
) -> dict[int, dict]:
    """Fetch app metadata and ratings using the iTunes lookup API."""
    ids = sorted(app_ids)
    results: dict[int, dict] = {}
    if not ids:
        return results

    batches = [ids[i : i + batch_size] for i in range(0, len(ids), batch_size)]

    def lookup_one(batch: list[int]) -> list[dict]:
        query = urllib.parse.urlencode(
            {"id": ",".join(str(i) for i in batch), "country": country, "entity": "software"}
        )
        url = f"https://itunes.apple.com/lookup?{query}"
        payload = _http_get_json(url)
        return payload.get("results", [])

    with ThreadPoolExecutor(max_workers=config.LOOKUP_WORKERS) as executor:
        futures = [executor.submit(lookup_one, batch) for batch in batches]
        for future in as_completed(futures):
            try:
                for item in future.result():
                    track_id = item.get("trackId")
                    if track_id is None:
                        continue
                    results[int(track_id)] = {
                        "bundle_id": item.get("bundleId"),
                        "name": item.get("trackName"),
                        "developer": item.get("artistName"),
                        "icon_url": item.get("artworkUrl100"),
                        "price_amount": _parse_float(item.get("price")),
                        "currency": item.get("currency"),
                        "rating": _parse_float(item.get("averageUserRating")),
                        "rating_count": item.get("userRatingCount"),
                    }
            except FetchError as exc:
                LOGGER.warning("rating lookup failed: %s", exc)
    return results


def _fetch_one(country: str, chart_type: str, genre: dict, limit: int) -> dict:
    try:
        app_ids = fetch_chart_ids(country, chart_type, genre["id"], limit=limit)
        entries = [{"app_id": app_id, "rank": index + 1} for index, app_id in enumerate(app_ids)]
    except FetchError:
        entries = fetch_feed(country, chart_type, genre["id"], limit=limit)
    return {
        "country": country,
        "chart_type": chart_type,
        "genre": genre,
        "entries": entries,
    }


def fetch_day(
    date: str,
    db_path: Path = config.DB_PATH,
    regions: list[str] | None = None,
    charts: list[str] | None = None,
    top_n: int = config.TOP_N,
    force: bool = False,
) -> dict:
    """Fetch daily snapshots for configured regions/charts and store them."""
    db.init_db(db_path)
    region_keys = regions or list(config.REGIONS.keys())
    chart_keys = charts or list(config.CHART_TYPES.keys())
    countries = [c for c in config.iter_countries() if c.region in region_keys]
    conn = db.connect(db_path)

    # 当天完整度判断：如果已抓取快照数达到预估完整阈值且未强制更新，则跳过
    if not force:
        existing_cnt = db.count_snapshots(conn, date, [c.code for c in countries], chart_keys)
        threshold = len(countries) * len(chart_keys) * 30
        if existing_cnt >= threshold and existing_cnt > 0:
            LOGGER.info(
                "App Store: date %s already complete (%s snapshots exist >= threshold %s). Skipping fetch.",
                date,
                existing_cnt,
                threshold,
            )
            conn.close()
            return {
                "date": date,
                "skipped": True,
                "reason": f"already complete ({existing_cnt} snapshots)",
                "countries": len(countries),
                "feeds_total": existing_cnt,
                "feeds_ok": existing_cnt,
                "feeds_failed": [],
                "entries_total": 0,
                "saved_snapshots": existing_cnt,
            }

    try:
        db.clear_snapshots(conn, date, [c.code for c in countries], chart_keys)
    finally:
        conn.close()

    stats = {
        "date": date,
        "regions": region_keys,
        "charts": chart_keys,
        "countries": len(countries),
        "feeds_total": 0,
        "feeds_ok": 0,
        "feeds_failed": [],
        "entries_total": 0,
        "saved_snapshots": 0,
    }
    fetched_at = datetime.now().astimezone().isoformat(timespec="seconds")

    for country in countries:
        try:
            genre_map = fetch_genre_map(country.code)
        except FetchError as exc:
            LOGGER.warning("genre map failed for %s: %s", country.code, exc)
            stats["feeds_failed"].append(f"{country.code}:genre-map:{exc}")
            continue

        genres = select_genres(genre_map)
        tasks = [
            (country.code, chart_type, genre, top_n)
            for chart_type in chart_keys
            for genre in genres
        ]
        stats["feeds_total"] += len(tasks)

        snapshots: list[tuple[str, str, str, str, list[dict]]] = []
        with ThreadPoolExecutor(max_workers=config.FEED_WORKERS) as executor:
            futures = [executor.submit(_fetch_one, *task) for task in tasks]
            for future in as_completed(futures):
                try:
                    result = future.result()
                    snapshots.append(
                        (
                            result["country"],
                            result["chart_type"],
                            result["genre"]["id"],
                            result["genre"]["name"],
                            result["entries"],
                        )
                    )
                    stats["feeds_ok"] += 1
                    stats["entries_total"] += len(result["entries"])
                except Exception as exc:  # noqa: BLE001 - keep going on per-feed failures
                    LOGGER.warning("feed failed: %s", exc)
                    stats["feeds_failed"].append(str(exc))

        app_ids = {
            entry["app_id"]
            for _, _, _, _, entries in snapshots
            for entry in entries
            if entry["app_id"]
        }
        details = fetch_ratings(country.code, app_ids)
        for entry in (e for _, _, _, _, entries in snapshots for e in entries):
            app_details = details.get(entry["app_id"], {})
            entry["bundle_id"] = app_details.get("bundle_id")
            entry["name"] = app_details.get("name")
            entry["developer"] = app_details.get("developer")
            entry["icon_url"] = app_details.get("icon_url")
            entry["price_amount"] = app_details.get("price_amount")
            entry["currency"] = app_details.get("currency")
            entry["rating"] = app_details.get("rating")
            entry["rating_count"] = app_details.get("rating_count")
            if not entry.get("name"):
                entry["name"] = f"App {entry['app_id']}"

        conn = db.connect(db_path)
        try:
            with conn:
                for country_code, chart_type, genre_id, genre_name, entries in snapshots:
                    db.replace_snapshot(
                        conn,
                        date,
                        country.region,
                        country_code,
                        chart_type,
                        genre_id,
                        genre_name,
                        entries,
                        fetched_at,
                    )
                    stats["saved_snapshots"] += 1
        finally:
            conn.close()

    return stats
