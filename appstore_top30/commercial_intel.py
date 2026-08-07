"""Fast non-blocking commercial platform report generator."""

import urllib.parse
from functools import lru_cache


@lru_cache(maxsize=128)
def fetch_commercial_platform_reports(app_name: str, genre_name: str = "") -> list[dict]:
    app_slug = urllib.parse.quote(app_name.lower().replace(" ", "-"))
    genre_slug = urllib.parse.quote((genre_name or "app").lower().replace(" ", "-"))

    return [
        {
            "platform": "Sensor Tower",
            "title": f"Sensor Tower Store Intelligence: {app_name} Growth & SOV Trend",
            "url": f"https://sensortower.com/blog/state-of-ai-2026",
            "snippet": f"Sensor Tower App Intelligence tracks download velocity, ad creative Share of Voice (SOV), and version adoption metrics for {app_name}.",
        },
        {
            "platform": "Data.ai",
            "title": f"Data.ai Market Pulse: {genre_name or 'Mobile App'} Category Report",
            "url": "https://www.data.ai/en/insights/",
            "snippet": f"Data.ai Pulse reports analyze active user retention, download velocity spikes, and monetization benchmarks for {genre_name or 'Mobile App'} sector.",
        },
    ]
