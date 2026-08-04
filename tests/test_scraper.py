import unittest

from appstore_top30 import scraper


SAMPLE_ENTRY = {
    "im:name": {"label": "Sample App"},
    "im:image": [
        {"label": "icon-53.png", "attributes": {"height": "53"}},
        {"label": "icon-100.png", "attributes": {"height": "100"}},
    ],
    "im:price": {
        "label": "Free",
        "attributes": {"amount": "0.00", "currency": "USD"},
    },
    "id": {
        "label": "https://apps.apple.com/us/app/sample/id123",
        "attributes": {"im:id": "123", "im:bundleId": "com.example.sample"},
    },
    "im:artist": {"label": "Example Developer"},
}


class ScraperTest(unittest.TestCase):
    def test_parse_feed_entry(self):
        parsed = scraper.parse_feed_entry(SAMPLE_ENTRY, rank=7)
        self.assertEqual(parsed["app_id"], 123)
        self.assertEqual(parsed["bundle_id"], "com.example.sample")
        self.assertEqual(parsed["name"], "Sample App")
        self.assertEqual(parsed["developer"], "Example Developer")
        self.assertEqual(parsed["icon_url"], "icon-100.png")
        self.assertEqual(parsed["price_amount"], 0.0)
        self.assertEqual(parsed["currency"], "USD")
        self.assertEqual(parsed["rank"], 7)

    def test_select_genres(self):
        genre_map = {
            "36": {"id": "36", "name": "App Store", "parent": None},
            "6000": {"id": "6000", "name": "Business", "parent": "36"},
            "6014": {"id": "6014", "name": "Games", "parent": "36"},
            "7001": {"id": "7001", "name": "Action", "parent": "6014"},
            "7002": {"id": "7002", "name": "Adventure", "parent": "6014"},
        }
        selected = scraper.select_genres(genre_map)
        self.assertEqual([g["id"] for g in selected], ["36", "6000", "6014", "7001", "7002"])


if __name__ == "__main__":
    unittest.main()
