"""Weather: real forecast from Open-Meteo (no API key) + transparent rule-based site assessment.

The thresholds below are generic rules of thumb. Always apply project-specific limits
and equipment manufacturer limits (e.g. crane wind limits).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DAILY_VARS = (
    "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
    "precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,uv_index_max"
)
ACTIVITIES = [
    "Concrete pouring",
    "Masonry / plastering",
    "Crane & lifting",
    "Work at height",
    "Excavation",
    "General outdoor labour",
]
_RANK = {"go": 0, "caution": 1, "no-go": 2}


class WeatherError(Exception):
    """Geocoding/forecast failure with a user-friendly message."""


@dataclass
class Thresholds:
    rain_caution_mm: float = 1.0
    rain_nogo_mm: float = 5.0
    rain_prob_caution: float = 50.0
    excavation_rain_caution_mm: float = 2.0
    excavation_rain_nogo_mm: float = 10.0
    gust_caution_kmh: float = 40.0
    gust_nogo_crane_kmh: float = 60.0
    gust_nogo_height_kmh: float = 50.0
    gust_caution_height_kmh: float = 35.0
    heat_caution_c: float = 35.0
    heat_nogo_c: float = 42.0
    concrete_heat_nogo_c: float = 40.0
    cold_caution_c: float = 5.0
    uv_high: float = 8.0


@dataclass
class DayForecast:
    date: str
    tmax: Optional[float]
    tmin: Optional[float]
    rain_mm: Optional[float]
    rain_prob: Optional[float]
    wind_kmh: Optional[float]
    gust_kmh: Optional[float]
    uv: Optional[float]
    code: Optional[int]

    @property
    def conditions(self) -> str:
        return wmo_text(self.code)


@dataclass
class DayAssessment:
    date: str
    statuses: Dict[str, str] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


def wmo_text(code: Optional[int]) -> str:
    if code is None:
        return "n/a"
    if code == 0:
        return "Clear"
    if code in (1, 2, 3):
        return "Partly cloudy"
    if code in (45, 48):
        return "Fog"
    if 51 <= code <= 57:
        return "Drizzle"
    if 61 <= code <= 67:
        return "Rain"
    if 71 <= code <= 77:
        return "Snow"
    if 80 <= code <= 82:
        return "Showers"
    if code in (85, 86):
        return "Snow showers"
    if code >= 95:
        return "Thunderstorm"
    return "Other (code %d)" % code


def _get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        resp = requests.get(url, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise WeatherError("Weather service unreachable or returned an error (%s)." % type(exc).__name__) from exc
    except ValueError as exc:
        raise WeatherError("Weather service returned invalid data.") from exc
    if not isinstance(data, dict):
        raise WeatherError("Weather service returned unexpected data.")
    return data


def geocode(place: str) -> Dict[str, Any]:
    if not place or not place.strip():
        raise WeatherError("Enter a location (city or town).")
    data = _get_json(GEOCODE_URL, {"name": place.strip(), "count": 1, "language": "en", "format": "json"})
    results = data.get("results") or []
    if not results:
        raise WeatherError("Location '%s' was not found." % place.strip())
    r = results[0]
    try:
        return {
            "name": ", ".join(p for p in (r.get("name"), r.get("admin1"), r.get("country")) if p),
            "lat": float(r["latitude"]),
            "lon": float(r["longitude"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherError("Geocoding result was incomplete.") from exc


def fetch_forecast(lat: float, lon: float, days: int = 7) -> List[DayForecast]:
    days = max(1, min(16, int(days)))
    data = _get_json(
        FORECAST_URL,
        {"latitude": lat, "longitude": lon, "daily": DAILY_VARS, "timezone": "auto", "forecast_days": days},
    )
    return parse_daily(data)


def parse_daily(data: Dict[str, Any]) -> List[DayForecast]:
    daily = data.get("daily")
    if not isinstance(daily, dict) or not daily.get("time"):
        raise WeatherError("Forecast response had no daily data.")

    def col(name: str) -> List[Any]:
        values = daily.get(name) or []
        return list(values) + [None] * (len(daily["time"]) - len(values))

    out: List[DayForecast] = []
    cols = {k: col(k) for k in (
        "temperature_2m_max", "temperature_2m_min", "precipitation_sum", "precipitation_probability_max",
        "wind_speed_10m_max", "wind_gusts_10m_max", "uv_index_max", "weather_code")}
    for i, day in enumerate(daily["time"]):
        code = cols["weather_code"][i]
        out.append(
            DayForecast(
                date=str(day),
                tmax=cols["temperature_2m_max"][i],
                tmin=cols["temperature_2m_min"][i],
                rain_mm=cols["precipitation_sum"][i],
                rain_prob=cols["precipitation_probability_max"][i],
                wind_kmh=cols["wind_speed_10m_max"][i],
                gust_kmh=cols["wind_gusts_10m_max"][i],
                uv=cols["uv_index_max"][i],
                code=int(code) if code is not None else None,
            )
        )
    return out


def _worst(a: str, b: str) -> str:
    return a if _RANK[a] >= _RANK[b] else b


def assess_day(d: DayForecast, th: Thresholds = Thresholds()) -> DayAssessment:
    """Rule-based go / caution / no-go per activity. Missing data never triggers a restriction."""
    s = {a: "go" for a in ACTIVITIES}
    notes: List[str] = []
    rain = d.rain_mm or 0.0
    prob = d.rain_prob or 0.0
    gust = d.gust_kmh or 0.0
    tmax, tmin = d.tmax, d.tmin

    if rain >= th.rain_nogo_mm:
        s["Concrete pouring"] = "no-go"
        s["Masonry / plastering"] = "no-go"
        notes.append("Heavy rain (%.1f mm): protect materials, avoid wet-work." % rain)
    elif rain >= th.rain_caution_mm or prob >= th.rain_prob_caution:
        s["Concrete pouring"] = _worst(s["Concrete pouring"], "caution")
        s["Masonry / plastering"] = _worst(s["Masonry / plastering"], "caution")
        notes.append("Rain possible (%.1f mm, %d%% chance): keep covers ready." % (rain, prob))
    if rain >= th.rain_nogo_mm:
        s["Work at height"] = _worst(s["Work at height"], "caution")
        notes.append("Wet, slippery surfaces: re-check access and edge protection.")
    if rain >= th.excavation_rain_nogo_mm:
        s["Excavation"] = "no-go"
        notes.append("Excavation: flooding / trench-collapse risk.")
    elif rain >= th.excavation_rain_caution_mm:
        s["Excavation"] = "caution"

    if gust >= th.gust_nogo_crane_kmh:
        s["Crane & lifting"] = "no-go"
    elif gust >= th.gust_caution_kmh:
        s["Crane & lifting"] = "caution"
    if gust >= th.gust_nogo_height_kmh:
        s["Work at height"] = "no-go"
    elif gust >= th.gust_caution_height_kmh:
        s["Work at height"] = _worst(s["Work at height"], "caution")
    if gust >= th.gust_caution_kmh:
        notes.append("Gusts up to %.0f km/h: check crane limits and secure loose materials." % gust)

    if tmax is not None:
        if tmax >= th.concrete_heat_nogo_c:
            s["Concrete pouring"] = "no-go"
            notes.append("Very hot (%.0f C): pour only at night/early morning with hot-weather measures." % tmax)
        elif tmax >= th.heat_caution_c:
            s["Concrete pouring"] = _worst(s["Concrete pouring"], "caution")
            s["Masonry / plastering"] = _worst(s["Masonry / plastering"], "caution")
            notes.append("Hot (%.0f C): hot-weather concreting, curing and hydration breaks." % tmax)
        if tmax >= th.heat_nogo_c:
            s["General outdoor labour"] = "no-go"
            notes.append("Extreme heat: restrict midday outdoor work.")
        elif tmax >= th.heat_caution_c:
            s["General outdoor labour"] = "caution"
    if tmin is not None and tmin <= th.cold_caution_c:
        s["Concrete pouring"] = _worst(s["Concrete pouring"], "caution")
        s["Masonry / plastering"] = _worst(s["Masonry / plastering"], "caution")
        notes.append("Low temperature (%.0f C): cold-weather concreting precautions." % tmin)
    if d.uv is not None and d.uv >= th.uv_high:
        notes.append("High UV index (%.0f): sun protection for outdoor crews." % d.uv)
    if d.code is not None and d.code >= 95:
        for a in ("Crane & lifting", "Work at height"):
            s[a] = "no-go"
        notes.append("Thunderstorm forecast: suspend lifting and work at height.")
    return DayAssessment(date=d.date, statuses=s, notes=notes)


def forecast_to_text(days: List[DayForecast], assessments: List[DayAssessment]) -> str:
    """Compact text of forecast + rule results (used in prompts)."""
    lines = []
    for d, a in zip(days, assessments):
        flags = ", ".join("%s=%s" % (k, v) for k, v in a.statuses.items() if v != "go") or "all go"
        lines.append(
            "%s: %s, Tmax %s, Tmin %s, rain %s mm (%s%%), gust %s km/h, UV %s | %s"
            % (d.date, d.conditions, d.tmax, d.tmin, d.rain_mm, d.rain_prob, d.gust_kmh, d.uv, flags)
        )
    return "\n".join(lines)
