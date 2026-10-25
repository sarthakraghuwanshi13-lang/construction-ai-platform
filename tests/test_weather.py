import unittest
from unittest import mock

import requests

from construction_ai import weather as W


def day(**kw):
    base = dict(date="2026-11-02", tmax=30.0, tmin=18.0, rain_mm=0.0, rain_prob=10.0,
                wind_kmh=10.0, gust_kmh=15.0, uv=5.0, code=1)
    base.update(kw)
    return W.DayForecast(**base)


class FakeResp:
    def __init__(self, payload, status=200):
        self.payload, self.status = payload, status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError("bad")

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class RuleTests(unittest.TestCase):
    def test_fair_day_all_go(self):
        a = W.assess_day(day())
        self.assertTrue(all(v == "go" for v in a.statuses.values()))

    def test_heavy_rain(self):
        a = W.assess_day(day(rain_mm=12.0))
        self.assertEqual(a.statuses["Concrete pouring"], "no-go")
        self.assertEqual(a.statuses["Excavation"], "no-go")
        self.assertEqual(a.statuses["Work at height"], "caution")

    def test_light_rain_chance_is_caution(self):
        a = W.assess_day(day(rain_mm=0.0, rain_prob=60.0))
        self.assertEqual(a.statuses["Concrete pouring"], "caution")

    def test_wind_and_storm(self):
        self.assertEqual(W.assess_day(day(gust_kmh=45)).statuses["Crane & lifting"], "caution")
        self.assertEqual(W.assess_day(day(gust_kmh=65)).statuses["Crane & lifting"], "no-go")
        self.assertEqual(W.assess_day(day(gust_kmh=55)).statuses["Work at height"], "no-go")
        self.assertEqual(W.assess_day(day(code=95)).statuses["Crane & lifting"], "no-go")

    def test_heat_and_cold(self):
        self.assertEqual(W.assess_day(day(tmax=37)).statuses["Concrete pouring"], "caution")
        self.assertEqual(W.assess_day(day(tmax=41)).statuses["Concrete pouring"], "no-go")
        self.assertEqual(W.assess_day(day(tmax=43)).statuses["General outdoor labour"], "no-go")
        self.assertEqual(W.assess_day(day(tmin=3)).statuses["Masonry / plastering"], "caution")

    def test_missing_data_never_restricts(self):
        a = W.assess_day(day(tmax=None, tmin=None, rain_mm=None, rain_prob=None, gust_kmh=None, uv=None, code=None))
        self.assertTrue(all(v == "go" for v in a.statuses.values()))

    def test_forecast_text(self):
        days = [day(rain_mm=12.0)]
        txt = W.forecast_to_text(days, [W.assess_day(days[0])])
        self.assertIn("2026-11-02", txt)
        self.assertIn("Concrete pouring=no-go", txt)


class NetworkTests(unittest.TestCase):
    def test_geocode_ok(self):
        payload = {"results": [{"name": "Bhopal", "admin1": "Madhya Pradesh", "country": "India", "latitude": 23.25, "longitude": 77.4}]}
        with mock.patch("requests.get", return_value=FakeResp(payload)):
            g = W.geocode("Bhopal")
        self.assertEqual(g["name"], "Bhopal, Madhya Pradesh, India")
        self.assertAlmostEqual(g["lat"], 23.25)

    def test_geocode_not_found_and_blank(self):
        with mock.patch("requests.get", return_value=FakeResp({})):
            with self.assertRaises(W.WeatherError):
                W.geocode("Nowhereville")
        with self.assertRaises(W.WeatherError):
            W.geocode("  ")

    def test_network_failure_is_friendly(self):
        with mock.patch("requests.get", side_effect=requests.ConnectionError("dns")):
            with self.assertRaises(W.WeatherError) as cm:
                W.geocode("Bhopal")
        self.assertIn("unreachable", str(cm.exception))
        with mock.patch("requests.get", return_value=FakeResp({}, status=500)):
            with self.assertRaises(W.WeatherError):
                W.fetch_forecast(1, 1)
        with mock.patch("requests.get", return_value=FakeResp(ValueError("bad json"))):
            with self.assertRaises(W.WeatherError):
                W.fetch_forecast(1, 1)

    def test_parse_daily_and_missing_columns(self):
        payload = {"daily": {"time": ["2026-11-02", "2026-11-03"], "temperature_2m_max": [30, 31],
                             "precipitation_sum": [0.0, 7.5], "weather_code": [0, 63]}}
        with mock.patch("requests.get", return_value=FakeResp(payload)):
            days = W.fetch_forecast(23.2, 77.4, 2)
        self.assertEqual(len(days), 2)
        self.assertEqual(days[1].rain_mm, 7.5)
        self.assertIsNone(days[0].gust_kmh)
        self.assertEqual(days[1].conditions, "Rain")
        with self.assertRaises(W.WeatherError):
            W.parse_daily({"daily": {}})


if __name__ == "__main__":
    unittest.main()
