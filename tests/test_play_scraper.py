import unittest
from unittest.mock import patch

from appstore_top30 import play_scraper


def _variant_a_item(app_id, title, developer, icon, price_text, currency, rating):
    price_pair = [None, currency, price_text]
    price_node = [[None, None, None, [None, None, [None, [price_pair]]]]]
    rating_pair = [None, rating]
    rating_node = [[None, None, [None, rating_pair]]]
    icon_node = [None, [[None, None, None, [None, None, icon]]]]
    return [
        None,
        icon_node,
        title,
        None,
        [[[developer]]],
        None,
        rating_node,
        price_node,
        None,
        None,
        None,
        None,
        [app_id],
    ]


def _variant_b_item(app_id, title, developer, icon, price_micros, currency, rating):
    head = [None] * 15
    head[0] = [app_id]
    head[1] = [None, None, None, [None, None, icon]]
    head[3] = title
    head[4] = [None, rating]
    head[8] = [None, [[price_micros, currency]]]
    head[14] = developer
    return [head]


def _page_html(app_items, key="ds:3"):
    import json

    payload = [[None, None, [None, app_items]]]
    return (
        "<!doctype html><html><body><script>"
        f"AF_initDataCallback({{key: '{key}', hash: 'abc', data: {json.dumps(payload)}, "
        "sideChannel: {}});"
        "</script></body></html>"
    )


def _batch_response(app_items):
    import json

    inner = [None] * 29
    inner[28] = [app_items]
    payload = [[None, [inner]]]
    line = json.dumps([["wrb.fr", "vyAe2", json.dumps(payload)]])
    return ")]}'\n\n" + str(len(line)) + "\n" + line + "\n25\n[['e',4,null,null,123]]\n"


class PlayScraperTest(unittest.TestCase):
    def test_parse_page_and_find_app_list(self):
        items = [
            _variant_a_item(
                "com.example.one", "One", "Dev One", "https://icon/1.png", "Free", "USD", 4.6
            ),
            _variant_a_item(
                "com.example.two", "Two", "Dev Two", "https://icon/2.png", "$1.99", "USD", 4.2
            ),
            _variant_a_item(
                "com.example.three", "Three", "Dev Three", "https://icon/3.png", "Free", "USD", 3.9
            ),
        ]
        parsed = play_scraper.parse_page(_page_html(items))
        self.assertIn("ds:3", parsed)
        app_list = play_scraper.find_app_list(parsed)
        self.assertEqual(len(app_list), 3)

    def test_parse_app_item_variant_a(self):
        item = _variant_a_item(
            "com.example.one", "One", "Dev One", "https://icon/1.png", "$2.99", "USD", 4.6
        )
        parsed = play_scraper.parse_app_item(item, rank=5)
        self.assertEqual(parsed["app_id"], "com.example.one")
        self.assertEqual(parsed["name"], "One")
        self.assertEqual(parsed["developer"], "Dev One")
        self.assertEqual(parsed["icon_url"], "https://icon/1.png")
        self.assertEqual(parsed["price_amount"], 2.99)
        self.assertEqual(parsed["currency"], "USD")
        self.assertEqual(parsed["rating"], 4.6)
        self.assertEqual(parsed["rank"], 5)

    def test_parse_app_item_variant_b(self):
        item = _variant_b_item(
            "com.example.two", "Two", "Dev Two", "https://icon/2.png", 4_990_000, "USD", 4.2
        )
        parsed = play_scraper.parse_app_item(item, rank=2)
        self.assertEqual(parsed["app_id"], "com.example.two")
        self.assertEqual(parsed["price_amount"], 4.99)
        self.assertEqual(parsed["currency"], "USD")

    def test_fetch_chart_uses_official_page_order(self):
        items = [
            _variant_a_item(
                "com.example.one", "One", "Dev One", "https://icon/1.png", "Free", "USD", 4.6
            ),
            _variant_a_item(
                "com.example.two", "Two", "Dev Two", "https://icon/2.png", "$1.99", "USD", 4.2
            ),
            _variant_a_item(
                "com.example.three", "Three", "Dev Three", "https://icon/3.png", "Free", "USD", 3.9
            ),
        ]
        with patch.object(play_scraper, "_http_get_text", return_value=_page_html(items)):
            entries = play_scraper.fetch_chart("us", "free", {"id": "all", "name": "总榜"}, top_n=3)
        self.assertEqual([entry["rank"] for entry in entries], [1, 2, 3])
        self.assertEqual(
            [entry["app_id"] for entry in entries],
            ["com.example.one", "com.example.two", "com.example.three"],
        )

    def test_batch_fetch_maps_all_category_to_application(self):
        items = [
            _variant_b_item(
                "com.example.one", "One", "Dev One", "https://icon/1.png", 0, "USD", 4.6
            ),
            _variant_b_item(
                "com.example.two", "Two", "Dev Two", "https://icon/2.png", 0, "USD", 4.2
            ),
        ]
        captured = {}

        def fake_post(url, body, **kwargs):
            captured["body"] = body
            return _batch_response(items)

        with patch.object(play_scraper, "_http_post", side_effect=fake_post):
            play_scraper._BUILD_LABEL = "test-build"
            raw = play_scraper._batch_fetch("gb", "free", "all", 2)
        self.assertEqual(len(raw), 2)
        self.assertIn("APPLICATION", captured["body"])
        entries = [play_scraper.parse_app_item(item, index + 1) for index, item in enumerate(raw)]
        self.assertEqual(entries[0]["app_id"], "com.example.one")

    def test_chart_url_and_categories(self):
        self.assertEqual(
            play_scraper.chart_url("us", "free", "all"),
            "https://play.google.com/store/apps/collection/topselling_free?hl=en&gl=us",
        )
        self.assertEqual(
            play_scraper.chart_url("jp", "grossing", "GAME"),
            "https://play.google.com/store/apps/category/GAME/collection/topgrossing?hl=en&gl=jp",
        )
        categories = play_scraper.select_play_categories()
        self.assertEqual(categories[0]["id"], "all")
        self.assertIn({"id": "GAME", "name": "游戏"}, categories)
        self.assertTrue(any(c["id"] == "GAME_CARD" for c in categories))


if __name__ == "__main__":
    unittest.main()
