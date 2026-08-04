"""Generate HTML and CSV daily reports."""

import csv
import html
import sqlite3
from pathlib import Path

from . import analyze, config, db

STATUS_LABELS = {
    "new": "新上榜",
    "left": "跌出榜单",
    "up": "上升",
    "down": "下降",
    "same": "持平",
}


def _query_rankings(
    conn: sqlite3.Connection,
    date: str,
    country: str,
    chart_type: str,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT r.rank_no, r.app_id, r.name, r.developer, r.price_amount,
               r.currency, r.rating, r.rating_count,
               s.genre_id, s.genre_name, a.bundle_id, a.icon_url
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
            "genre_name": config.genre_display_name(row["genre_id"], row["genre_name"]),
        }
        for row in rows
    ]


def write_rankings_csv(
    conn: sqlite3.Connection,
    date: str,
    country: str,
    chart_type: str,
    path: Path,
) -> None:
    rows = _query_rankings(conn, date, country, chart_type)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "country",
                "chart_type",
                "genre_id",
                "genre_name",
                "rank",
                "app_id",
                "bundle_id",
                "name",
                "developer",
                "icon_url",
                "price_amount",
                "currency",
                "rating",
                "rating_count",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    country,
                    chart_type,
                    row["genre_id"],
                    row["genre_name"],
                    row["rank_no"],
                    row["app_id"],
                    row.get("bundle_id"),
                    row.get("name"),
                    row.get("developer"),
                    row.get("icon_url"),
                    row.get("price_amount"),
                    row.get("currency"),
                    row.get("rating"),
                    row.get("rating_count"),
                ]
            )


def write_changes_csv(changes: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "app_id",
                "name",
                "developer",
                "icon_url",
                "genre_name",
                "status",
                "prev_rank",
                "curr_rank",
                "rank_change",
                "prev_price_amount",
                "price_amount",
                "price_change",
                "prev_rating",
                "rating",
                "rating_change",
            ]
        )
        for change in changes:
            writer.writerow(
                [
                    change.get("app_id"),
                    change.get("name"),
                    change.get("developer"),
                    change.get("icon_url"),
                    change.get("genre_name"),
                    change.get("status"),
                    change.get("prev_rank"),
                    change.get("curr_rank"),
                    change.get("rank_change"),
                    change.get("prev_price_amount"),
                    change.get("price_amount"),
                    change.get("price_change"),
                    change.get("prev_rating"),
                    change.get("rating"),
                    change.get("rating_change"),
                ]
            )


def write_summary_csv(summaries: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "region",
                "country",
                "country_name",
                "chart_type",
                "has_previous",
                "genres",
                "entries",
                "new",
                "left",
                "up",
                "down",
                "same",
            ]
        )
        for summary in summaries:
            writer.writerow(
                [
                    summary["region"],
                    summary["country"],
                    summary["country_name"],
                    summary["chart"],
                    summary["has_previous"],
                    summary["genres"],
                    summary["entries"],
                    summary["new"],
                    summary["left"],
                    summary["up"],
                    summary["down"],
                    summary["same"],
                ]
            )


def write_region_summary_csv(summaries: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "region",
                "region_name",
                "chart_type",
                "rank",
                "app_id",
                "name",
                "developer",
                "country_count",
                "avg_rank",
                "best_rank",
                "best_country",
                "genres",
            ]
        )
        for summary in summaries:
            for index, app in enumerate(summary["apps"], start=1):
                writer.writerow(
                    [
                        summary["region"],
                        summary["region_name"],
                        summary["chart"],
                        index,
                        app["app_id"],
                        app.get("name"),
                        app.get("developer"),
                        app["country_count"],
                        app["avg_rank"],
                        app["best_rank"],
                        app.get("best_country"),
                        app.get("genres"),
                    ]
                )


def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


def _price(amount, currency) -> str:
    if amount is None:
        return "-"
    text = f"{float(amount):.2f}"
    if currency:
        text += f" {currency}"
    return text


def _rank_change_text(change: dict) -> str:
    value = change.get("rank_change")
    if value is None:
        return "-"
    if value > 0:
        return f"▲ {value}"
    if value < 0:
        return f"▼ {abs(value)}"
    return "0"


def _movers_table(changes: list[dict]) -> str:
    rows = analyze.top_movers(changes, limit=15)
    if not rows:
        return "<p class=\"empty\">暂无可对比数据</p>"
    lines = [
        "<table><thead><tr>"
        "<th>应用</th><th>开发者</th><th>分类</th><th>昨日</th><th>今日</th>"
        "<th>变化</th><th>价格变化</th><th>评分变化</th>"
        "</tr></thead><tbody>"
    ]
    for change in rows:
        rating_change = change.get("rating_change")
        rating_text = f"{rating_change:+.2f}" if rating_change is not None else "-"
        price_change = change.get("price_change")
        price_text = f"{price_change:+.2f}" if price_change is not None else "-"
        lines.append(
            "<tr>"
            f"<td>{_esc(change.get('name'))}</td>"
            f"<td>{_esc(change.get('developer'))}</td>"
            f"<td>{_esc(change.get('genre_name'))}</td>"
            f"<td>{_esc(change.get('prev_rank'))}</td>"
            f"<td>{_esc(change.get('curr_rank'))}</td>"
            f"<td>{_rank_change_text(change)}</td>"
            f"<td>{_esc(price_text)}</td>"
            f"<td>{_esc(rating_text)}</td>"
            "</tr>"
        )
    lines.append("</tbody></table>")
    return "\n".join(lines)


def _new_table(changes: list[dict]) -> str:
    rows = analyze.top_new_entries(changes, limit=15)
    if not rows:
        return "<p class=\"empty\">今日无新上榜应用</p>"
    lines = [
        "<table><thead><tr>"
        "<th>排名</th><th>应用</th><th>开发者</th><th>分类</th><th>价格</th><th>评分</th>"
        "</tr></thead><tbody>"
    ]
    for change in rows:
        rating = change.get("rating")
        rating_text = f"{rating:.2f}" if rating is not None else "-"
        lines.append(
            "<tr>"
            f"<td>{_esc(change.get('curr_rank'))}</td>"
            f"<td>{_esc(change.get('name'))}</td>"
            f"<td>{_esc(change.get('developer'))}</td>"
            f"<td>{_esc(change.get('genre_name'))}</td>"
            f"<td>{_esc(_price(change.get('price_amount'), change.get('price_currency')))}</td>"
            f"<td>{_esc(rating_text)}</td>"
            "</tr>"
        )
    lines.append("</tbody></table>")
    return "\n".join(lines)


def _left_table(changes: list[dict]) -> str:
    rows = analyze.top_left_entries(changes, limit=15)
    if not rows:
        return "<p class=\"empty\">今日无跌出榜单应用</p>"
    lines = [
        "<table><thead><tr>"
        "<th>昨日排名</th><th>应用</th><th>开发者</th><th>分类</th><th>昨日价格</th>"
        "</tr></thead><tbody>"
    ]
    for change in rows:
        lines.append(
            "<tr>"
            f"<td>{_esc(change.get('prev_rank'))}</td>"
            f"<td>{_esc(change.get('name'))}</td>"
            f"<td>{_esc(change.get('developer'))}</td>"
            f"<td>{_esc(change.get('genre_name'))}</td>"
            f"<td>{_esc(_price(change.get('prev_price_amount'), change.get('price_currency')))}</td>"
            "</tr>"
        )
    lines.append("</tbody></table>")
    return "\n".join(lines)


def _rating_table(changes: list[dict]) -> str:
    rows = analyze.top_rating_changes(changes, limit=10)
    if not rows:
        return "<p class=\"empty\">今日无评分变化</p>"
    lines = [
        "<table><thead><tr>"
        "<th>应用</th><th>开发者</th><th>分类</th><th>昨日评分</th><th>今日评分</th><th>变化</th>"
        "</tr></thead><tbody>"
    ]
    for change in rows:
        prev_rating = change.get("prev_rating")
        rating = change.get("rating")
        rating_change = change.get("rating_change")
        rating_change_text = f"{rating_change:+.2f}" if rating_change is not None else "-"
        lines.append(
            "<tr>"
            f"<td>{_esc(change.get('name'))}</td>"
            f"<td>{_esc(change.get('developer'))}</td>"
            f"<td>{_esc(change.get('genre_name'))}</td>"
            f"<td>{_esc(f'{prev_rating:.2f}' if prev_rating is not None else '-')}</td>"
            f"<td>{_esc(f'{rating:.2f}' if rating is not None else '-')}</td>"
            f"<td>{_esc(rating_change_text)}</td>"
            "</tr>"
        )
    lines.append("</tbody></table>")
    return "\n".join(lines)


def _country_section(
    summary_group: dict,
    date: str,
    country: str,
) -> str:
    region_order = list(config.REGIONS.keys())
    charts_html = []
    for index, summary in enumerate(summary_group):
        open_attr = " open" if index == 0 else ""
        changes = summary.get("changes", [])
        charts_html.append(
            "<details class=\"chart\"" + open_attr + ">"
            f"<summary>{_esc(summary['chart_name'])}"
            f"<span class=\"meta\">分类 {summary['genres']} · 应用 {summary['entries']}"
            f" · 新 {summary['new']} · 跌出 {summary['left']}"
            f" · 升 {summary['up']} · 降 {summary['down']}</span></summary>"
            "<div class=\"chart-body\">"
            "<h4>排名变动 Top 15</h4>"
            + _movers_table(changes)
            + "<h4>新上榜 Top 15</h4>"
            + _new_table(changes)
            + "<h4>跌出榜单 Top 15</h4>"
            + _left_table(changes)
            + "<h4>评分变化 Top 10</h4>"
            + _rating_table(changes)
            + "</div></details>"
        )

    region_name = config.REGIONS.get(
        summary_group[0]["region"], {}
    ).get("name", summary_group[0]["region"])
    country_heading = f"{summary_group[0]['country_name']} <span class=\"muted\">{region_name}</span>"
    return (
        "<section class=\"country\">"
        f"<h3>{country_heading}</h3>"
        + "\n".join(charts_html)
        + "</section>"
    )


def _region_table(summary: dict) -> str:
    rows = summary["apps"][:15]
    if not rows:
        return "<p class=\"empty\">该地区暂无榜单数据</p>"
    lines = [
        "<table><thead><tr>"
        "<th>排名</th><th>应用</th><th>开发者</th><th>国家数</th><th>平均排名</th><th>最佳排名</th><th>主要分类</th>"
        "</tr></thead><tbody>"
    ]
    for index, app in enumerate(rows, start=1):
        lines.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{_esc(app.get('name'))}</td>"
            f"<td>{_esc(app.get('developer'))}</td>"
            f"<td>{app['country_count']}</td>"
            f"<td>{_esc(app['avg_rank'])}</td>"
            f"<td>{app['best_rank']}</td>"
            f"<td>{_esc(app.get('genres'))}</td>"
            "</tr>"
        )
    lines.append("</tbody></table>")
    return "\n".join(lines)


def _region_sections(region_summaries: list[dict]) -> str:
    by_region: dict[str, list[dict]] = {}
    for summary in region_summaries:
        by_region.setdefault(summary["region"], []).append(summary)

    sections = []
    for region in config.REGIONS:
        group = by_region.get(region, [])
        if not group:
            continue
        charts_html = []
        for summary in group:
            charts_html.append(
                "<details class=\"chart\"><summary>"
                f"{_esc(summary['chart_name'])}"
                f"<span class=\"meta\">覆盖 {summary['country_count']} 个国家</span></summary>"
                "<div class=\"chart-body\">"
                + _region_table(summary)
                + "</div></details>"
            )
        sections.append(
            "<section class=\"region\">"
            f"<h2>{_esc(config.REGIONS[region]['name'])}</h2>"
            + "\n".join(charts_html)
            + "</section>"
        )
    return "\n".join(sections)


def _summary_cards(summaries: list[dict], counts: dict, date: str, prev_date: str | None) -> str:
    total_new = sum(s["new"] for s in summaries)
    total_left = sum(s["left"] for s in summaries)
    total_up = sum(s["up"] for s in summaries)
    total_down = sum(s["down"] for s in summaries)
    total_same = sum(s["same"] for s in summaries)
    cards = [
        ("报告日期", date),
        ("对比日期", prev_date or "首次采集"),
        ("国家数", str(counts.get("countries", 0))),
        ("榜单快照", str(counts.get("snapshots", 0))),
        ("榜单条目", str(counts.get("entries", 0))),
        ("新上榜", str(total_new)),
        ("跌出榜单", str(total_left)),
        ("排名上升", str(total_up)),
        ("排名下降", str(total_down)),
        ("排名持平", str(total_same)),
    ]
    items = []
    for label, value in cards:
        items.append(
            f"<div class=\"card\"><span class=\"label\">{_esc(label)}</span>"
            f"<span class=\"value\">{_esc(value)}</span></div>"
        )
    return "<div class=\"cards\">" + "\n".join(items) + "</div>"


def _file_links(report_dir: Path, summaries: list[dict]) -> str:
    items = []
    for summary in summaries:
        country = summary["country"]
        chart = summary["chart"]
        items.append(
            "<li>"
            f"<a href=\"rankings_{country}_{chart}.csv\">rankings_{country}_{chart}.csv</a>"
            " · "
            f"<a href=\"changes_{country}_{chart}.csv\">changes_{country}_{chart}.csv</a>"
            "</li>"
        )
    items.append("<li><a href=\"summary.csv\">summary.csv</a></li>")
    items.append("<li><a href=\"region_summary.csv\">region_summary.csv</a></li>")
    return "<ul class=\"files\">" + "\n".join(items) + "</ul>"


def _render_html(
    date: str,
    prev_date: str | None,
    summaries: list[dict],
    counts: dict,
    report_dir: Path,
    region_summaries: list[dict],
) -> str:
    by_region: dict[str, list[dict]] = {}
    for summary in summaries:
        by_region.setdefault(summary["region"], []).append(summary)

    region_order = list(config.REGIONS.keys())
    regions_html = []
    for region in region_order:
        if region not in by_region:
            continue
        name = config.REGIONS[region]["name"]
        countries_html = []
        for country_code, _ in config.REGIONS[region]["countries"]:
            group = [s for s in by_region[region] if s["country"] == country_code]
            if group and any(s["entries"] > 0 for s in group):
                countries_html.append(_country_section(group, date, country_code))
        if countries_html:
            regions_html.append(
                f"<section class=\"region\"><h2>{_esc(name)}</h2>"
                + "\n".join(countries_html)
                + "</section>"
            )

    header_subtitle = (
        f"数据日期 {date}" + (f" · 对比 {prev_date}" if prev_date else " · 首次采集，暂无环比")
    )
    regions_joined = "\n".join(regions_html)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>App Store Top 30 每日分析 - {_esc(date)}</title>
<style>
:root {{ color-scheme: light; }}
body {{ font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; margin: 0; color: #1f2328; background: #f6f7f9; }}
header {{ background: #111827; color: #fff; padding: 28px 32px; }}
header h1 {{ margin: 0 0 6px; font-size: 24px; font-weight: 600; }}
header p {{ margin: 0; color: #9ca3af; font-size: 14px; }}
main {{ max-width: 1200px; margin: 0 auto; padding: 24px 32px 48px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 20px 0; }}
.card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px; }}
.card .label {{ display: block; color: #6b7280; font-size: 12px; margin-bottom: 4px; }}
.card .value {{ font-size: 20px; font-weight: 600; }}
.files {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px 14px 14px 34px; font-size: 13px; }}
.files li {{ margin: 3px 0; }}
section.region {{ margin-top: 32px; }}
section.region > h2 {{ font-size: 20px; margin: 0 0 12px; border-bottom: 2px solid #111827; padding-bottom: 6px; }}
section.country {{ margin: 18px 0; }}
section.country > h3 {{ margin: 0 0 10px; font-size: 16px; }}
.muted {{ color: #6b7280; font-weight: 400; font-size: 13px; margin-left: 6px; }}
details.chart {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; margin: 10px 0; }}
details.chart summary {{ cursor: pointer; padding: 12px 16px; font-weight: 600; font-size: 15px; }}
details.chart summary .meta {{ display: block; font-weight: 400; color: #6b7280; font-size: 12px; margin-top: 2px; }}
.chart-body {{ padding: 4px 16px 16px; }}
.chart-body h4 {{ margin: 18px 0 8px; font-size: 14px; color: #111827; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ border-bottom: 1px solid #eef0f2; padding: 7px 8px; text-align: left; vertical-align: top; }}
th {{ color: #6b7280; font-weight: 500; background: #fafbfc; }}
td:first-child, th:first-child {{ padding-left: 10px; }}
td:nth-child(4), td:nth-child(5), td:nth-child(6) {{ white-space: nowrap; }}
.empty {{ color: #6b7280; font-size: 13px; margin: 8px 0; }}
footer {{ max-width: 1200px; margin: 0 auto; padding: 0 32px 40px; color: #6b7280; font-size: 12px; }}
</style>
</head>
<body>
<header>
<h1>App Store Top 30 每日分析</h1>
<p>{_esc(header_subtitle)}</p>
</header>
<main>
{_summary_cards(summaries, counts, date, prev_date)}
<h2>数据文件</h2>
{_file_links(report_dir, summaries)}
<h2>地区汇总</h2>
{_region_sections(region_summaries)}
<h2>国家明细</h2>
{regions_joined}
</main>
<footer>数据来源：Apple iTunes RSS / Lookup 公开接口；报告为本地生成，仅用于个人分析。</footer>
</body>
</html>
"""


def generate_report(
    date: str,
    db_path: Path = config.DB_PATH,
    reports_dir: Path = config.REPORTS_DIR,
) -> Path:
    db.init_db(db_path)
    report_dir = reports_dir / date
    report_dir.mkdir(parents=True, exist_ok=True)
    for path in list(report_dir.glob("rankings_*.csv")) + list(report_dir.glob("changes_*.csv")) + list(
        report_dir.glob("summary.csv")
    ) + list(report_dir.glob("region_summary.csv")) + list(
        report_dir.glob("report_*.html")
    ):
        path.unlink()

    conn = db.connect(db_path)
    try:
        prev_date = db.get_previous_date(conn, date)
        summaries = analyze.build_all_summaries(conn, date, prev_date)
        region_summaries = analyze.build_all_region_summaries(conn, date)
        counts = db.snapshot_counts(conn, date)
        active_summaries = [s for s in summaries if s["entries"] > 0]

        write_summary_csv(summaries, report_dir / "summary.csv")
        write_region_summary_csv(region_summaries, report_dir / "region_summary.csv")
        for summary in active_summaries:
            country = summary["country"]
            chart = summary["chart"]
            write_rankings_csv(conn, date, country, chart, report_dir / f"rankings_{country}_{chart}.csv")
            write_changes_csv(summary.get("changes", []), report_dir / f"changes_{country}_{chart}.csv")
    finally:
        conn.close()

    html_path = report_dir / f"report_{date}.html"
    html_path.write_text(
        _render_html(date, prev_date, active_summaries, counts, report_dir, region_summaries),
        encoding="utf-8",
    )
    return html_path
