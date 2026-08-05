import unittest

from appstore_top30 import config


class ConfigTest(unittest.TestCase):
    def test_region_packages(self):
        self.assertEqual(len(config.REGIONS), 9)
        self.assertIn(("mx", "墨西哥"), config.REGIONS["latam"]["countries"])
        self.assertIn(("kr", "韩国"), config.REGIONS["east_asia"]["countries"])
        self.assertIn(("eg", "埃及"), config.REGIONS["mena"]["countries"])

    def test_countries_are_unique(self):
        countries = config.iter_countries()
        codes = [country.code for country in countries]
        self.assertEqual(len(countries), 39)
        self.assertEqual(len(set(codes)), len(codes))


if __name__ == "__main__":
    unittest.main()
