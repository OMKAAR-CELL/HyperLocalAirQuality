"""Simple trend forecast (least-squares line over recent readings).

This is deliberately basic and labelled a 'trend forecast'. When real sensor data exists
it can be replaced by an ANN trained offline (see README).
"""


def _fit_line(xs, ys):
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var = sum((x - mean_x) ** 2 for x in xs)
    if var == 0:
        return 0.0, mean_y
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / var
    return slope, mean_y - slope * mean_x


def forecast(readings, minutes_ahead=60, window_minutes=90):
    """readings: list of Reading objects, oldest first. Returns a dict or None."""
    if len(readings) < 5:
        return None
    latest = readings[-1].created_at
    recent = [r for r in readings if (latest - r.created_at).total_seconds() <= window_minutes * 60]
    if len(recent) < 5:
        recent = readings[-20:]
    t0 = recent[0].created_at
    xs = [(r.created_at - t0).total_seconds() / 60 for r in recent]
    target_x = xs[-1] + minutes_ahead

    out = {"minutes_ahead": minutes_ahead, "method": "linear trend (demo forecast)"}
    for field, lo, hi in (("co2", 400, 5000), ("pm25", 0, 500)):
        ys = [getattr(r, field) for r in recent]
        slope, intercept = _fit_line(xs, ys)
        pred = max(lo, min(hi, slope * target_x + intercept))
        out[field] = round(pred)
        out[field + "_trend"] = "rising" if slope * 60 > 0.03 * max(ys[-1], 1) else (
            "falling" if slope * 60 < -0.03 * max(ys[-1], 1) else "steady")
    return out
