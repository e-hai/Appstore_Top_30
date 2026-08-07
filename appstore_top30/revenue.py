"""Rough monthly revenue estimates based on Top Grossing chart positions.

These numbers are deliberately coarse reference bands calibrated against
publicly known magnitudes for top grossing charts and market size tiers.
They are estimates only and must never be presented as real financial data.
"""

import math

GROSSING_CHART = "grossing"

# Country tier -> configured country codes. Tiers are ordered by typical
# consumer spending power in the mobile app market.
COUNTRY_TIERS = {
    "t1": {"us", "jp"},
    "t2": {
        "gb", "de", "fr", "kr", "ca", "au", "tw", "hk", "sg", "sa", "ae", "il",
    },
    "t3": {
        "mx", "br", "tr", "it", "es", "ar", "cl", "co", "pe",
        "th", "my", "id", "vn", "ph", "in", "za", "nz", "mo",
    },
    "t4": {"eg", "ma", "pk", "bd", "lk", "ng", "ke"},
}

TIER_LABELS = {
    "t1": "头部市场",
    "t2": "高价值市场",
    "t3": "成长市场",
    "t4": "新兴市场",
}

# Approximate monthly gross revenue in USD at ranks 1/10/30 for each tier.
_ANCHORS = {
    "t1": (20_000_000, 4_000_000, 1_000_000),
    "t2": (6_000_000, 1_200_000, 300_000),
    "t3": (2_000_000, 400_000, 100_000),
    "t4": (600_000, 120_000, 30_000),
}

# Google Play tends to monetize lower than the App Store in most markets.
_PLAY_FACTOR = 0.7


def country_tier(country: str) -> str:
    for tier, codes in COUNTRY_TIERS.items():
        if country.lower() in codes:
            return tier
    return "t3"


def _round_sig(value: float, sig: int = 2) -> int:
    if value <= 0:
        return 0
    digits = sig - int(math.floor(math.log10(value))) - 1
    return int(round(value, digits))


def _midpoint(rank: int, tier: str) -> float:
    rank_1, rank_10, rank_30 = _ANCHORS[tier]
    if rank <= 10:
        return rank_1 * (rank_10 / rank_1) ** ((rank - 1) / 9)
    return rank_10 * (rank_30 / rank_10) ** ((rank - 10) / 20)


def format_revenue(value: float) -> str:
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:.0f}k"
    return f"${value:,.0f}"


def format_revenue_range(low: float, high: float) -> str:
    return f"{format_revenue(low)}-{format_revenue(high)}"


def estimate_monthly_revenue(
    rank,
    country: str,
    chart_type: str,
    store: str = "app_store",
) -> dict | None:
    if chart_type != GROSSING_CHART:
        return None
    try:
        rank = int(rank)
    except (TypeError, ValueError):
        return None
    if rank < 1 or rank > 30:
        return None

    factor = _PLAY_FACTOR if store == "play" else 1.0
    tier = country_tier(country)
    mid = _midpoint(rank, tier) * factor
    low = _round_sig(mid * 0.55)
    high = _round_sig(mid * 1.65)
    if high <= low:
        high = low + 1
    return {
        "low": low,
        "high": high,
        "mid": _round_sig(mid),
        "tier": tier,
        "tier_label": TIER_LABELS[tier],
        "text": format_revenue_range(low, high),
    }


def attach_revenue_estimates(
    changes: list[dict],
    country: str,
    chart_type: str,
    store: str = "app_store",
) -> list[dict]:
    for change in changes:
        change["monthly_revenue"] = estimate_monthly_revenue(
            change.get("curr_rank"),
            country,
            chart_type,
            store=store,
        )
    return changes
