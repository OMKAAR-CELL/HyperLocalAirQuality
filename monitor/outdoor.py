"""Outdoor air quality from Open-Meteo (free, no API key).

Note: this is modelled city-level data, not a ground sensor. If the call fails we keep the last
good value; if there is none at all we store a clearly labelled fallback so the demo still runs.
"""
import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

from .models import OutdoorReading

log = logging.getLogger(__name__)
URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
_last_attempt = None


def fetch_outdoor():
    """Call the API and save a row. Returns the row or None on failure."""
    try:
        resp = requests.get(
            URL,
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
    except Exception as exc:  # network down, bad JSON, rate limit...
        log.warning("Outdoor fetch failed: %s", exc)
        return None


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
