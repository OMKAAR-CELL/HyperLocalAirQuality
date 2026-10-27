"""Rule engine: turns indoor + outdoor readings into a status level and plain advice."""

CO2_OK = 800
CO2_HIGH = 1200
PM_OK = 60       # ug/m3
PM_HIGH = 120
OUTDOOR_BAD_PM = 60


def level_for(indoor):
    """green / yellow / red from indoor readings only (same thresholds as the LED on the device)."""
    if indoor is None:
        return "unknown"
    if indoor["co2"] > CO2_HIGH or indoor["pm25"] > PM_HIGH:
        return "red"
    if indoor["co2"] >= CO2_OK or indoor["pm25"] >= PM_OK:
        return "yellow"
    return "green"


def advice_for(indoor, outdoor):
    """Return a short, plain-English recommendation."""
    if indoor is None:
        return "No indoor data yet."

    co2_high = indoor["co2"] >= CO2_OK
    pm_high = indoor["pm25"] >= PM_OK
    outdoor_pm = outdoor["pm25"] if outdoor else None
    outdoor_bad = outdoor_pm is not None and outdoor_pm >= OUTDOOR_BAD_PM

    if pm_high:
        return "Indoor dust is high. Keep windows closed and check for a source (dust, smoke, cooking)."
    if co2_high and outdoor_pm is None:
        return "CO2 is building up. Ventilate briefly. Outdoor data is unavailable, so check the outdoor AQI first."
    if co2_high and not outdoor_bad:
        return "CO2 is high and the outdoor air is reasonably clean. Open the windows for a few minutes."
    if co2_high and outdoor_bad:
        return ("CO2 is high but the outdoor air is polluted. Ventilate in short bursts, "
                "use a purifier or mask, and avoid leaving windows open for long.")
    return "Air quality is good. No action needed."
