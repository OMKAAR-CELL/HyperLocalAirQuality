"""Outdoor air quality.

Primary source: the nearest government ground station via WAQI (aqicn.org), which relays
CPCB/UPPCB readings. Needs a free token in the WAQI_TOKEN setting.
Fallback: Open-Meteo modelled data (free, no key). It is coarse city-level model output and
can under-read during severe NCR winter episodes, so it is only used when WAQI is unavailable.

If every call fails we keep the last good value; if there is none at all we return the newest
stored row, flagged as stale, so the demo still runs.
"""
import logging
from datetime import datetime, timedelta, timezone as dt_timezone

import requests
from django.conf import settings
from django.utils import timezone

from .models import OutdoorReading

log = logging.getLogger(__name__)

WAQI_URL = "https://api.waqi.info/feed/geo:{lat};{lon}/"
OPEN_METEO_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
MAX_STATION_AGE = timedelta(hours=6)   # ignore station data older than this
_last_attempt = None

# US EPA breakpoints: (conc_low, conc_high, aqi_low, aqi_high)
PM25_BREAKPOINTS = [
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 350.4, 301, 400),
    (350.5, 500.4, 401, 500),
]
PM10_BREAKPOINTS = [
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 504, 301, 400),
    (505, 604, 401, 500),
]


def aqi_to_conc(aqi, table):
    """Convert a US-AQI sub-index back to ug/m3 (approximate)."""
    aqi = max(0.0, float(aqi))
    for c_lo, c_hi, i_lo, i_hi in table:
        if aqi <= i_hi:
            return c_lo + (aqi - i_lo) * (c_hi - c_lo) / (i_hi - i_lo)
    return float(table[-1][1])


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_waqi():
    """Nearest ground station via WAQI. Returns a saved row, or None."""
    token = getattr(settings, "WAQI_TOKEN", "")
    if not token:
        return None
    try:
        resp = requests.get(
            WAQI_URL.format(lat=settings.OUTDOOR_LAT, lon=settings.OUTDOOR_LON),
            params={"token": token},
            timeout=8,
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("status") != "ok":
            raise ValueError(f"WAQI error: {payload.get('data')}")
        data = payload["data"]
        iaqi = data.get("iaqi", {})

        pm25_aqi = _num(iaqi.get("pm25", {}).get("v"))
        if pm25_aqi is None:
            raise ValueError("nearest station has no PM2.5")

        stamp = (data.get("time") or {}).get("iso")
        if stamp:
            measured = datetime.fromisoformat(stamp)
            if measured.tzinfo is None:
                measured = measured.replace(tzinfo=dt_timezone.utc)
            if timezone.now() - measured > MAX_STATION_AGE:
                raise ValueError(f"station data too old ({stamp})")

        pm10_aqi = _num(iaqi.get("pm10", {}).get("v"))
        station = (data.get("city") or {}).get("name") or "station"
        return OutdoorReading.objects.create(
            pm25=round(aqi_to_conc(pm25_aqi, PM25_BREAKPOINTS), 1),
            pm10=None if pm10_aqi is None else round(aqi_to_conc(pm10_aqi, PM10_BREAKPOINTS), 1),
            aqi=_num(data.get("aqi")),
            source=("waqi: " + station)[:32],
        )
    except Exception as exc:
        log.warning("WAQI fetch failed: %s", exc)
        return None


def fetch_open_meteo():
    """Modelled data fallback. Returns a saved row, or None."""
    try:
        resp = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": settings.OUTDOOR_LAT,
                "longitude": settings.OUTDOOR_LON,
                "current": "pm2_5,pm10,us_aqi",
            },
            timeout=6,
        )
        resp.raise_for_status()
        cur = resp.json()["current"]
        return OutdoorReading.objects.create(
            pm25=float(cur["pm2_5"]),
            pm10=None if cur.get("pm10") is None else float(cur["pm10"]),
            aqi=None if cur.get("us_aqi") is None else float(cur["us_aqi"]),
            source="open-meteo",
        )
    except Exception as exc:
        log.warning("Open-Meteo fetch failed: %s", exc)
        return None


def fetch_outdoor():
    """Ground station first, modelled data as fallback. Returns the row or None."""
    return fetch_waqi() or fetch_open_meteo()


def latest_outdoor(refresh=True):
    """Latest outdoor row, refreshing lazily if it is older than OUTDOOR_REFRESH_MIN.

    Returns (row_or_None, is_stale).
    """
    global _last_attempt
    last = OutdoorReading.objects.exclude(source="simulated").order_by("-created_at").first()
    max_age = timedelta(minutes=settings.OUTDOOR_REFRESH_MIN)
    now = timezone.now()
    needs_refresh = last is None or now - last.created_at > max_age
    # back off for 2 minutes after a failed attempt so a dead API never slows the dashboard
    if refresh and needs_refresh and (_last_attempt is None or now - _last_attempt > timedelta(minutes=2)):
        _last_attempt = now
        fresh = fetch_outdoor()
        if fresh:
            return fresh, False
    if last is not None:
        return last, timezone.now() - last.created_at > max_age * 3

    # No real outdoor data at all: fall back to the newest seeded/simulated row, flagged as such.
    sim = OutdoorReading.objects.order_by("-created_at").first()
    return sim, True
