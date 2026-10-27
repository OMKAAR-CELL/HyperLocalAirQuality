"""Demo-data model: plausible indoor readings that follow the outdoor air.

Pure Python, no Django imports, so both the seed command and the live simulator can use it.
All data produced here is labelled source="simulated" when it is stored.
"""
import math
import random


def outdoor_pm25(hour_float, rng=random):
    """Synthetic outdoor PM2.5 for NCR in autumn/winter: peaks in early morning and late night."""
    morning = 45 * math.exp(-((hour_float - 7.0) ** 2) / 8)
    night = 55 * math.exp(-((hour_float - 23.0) ** 2) / 10)
    night2 = 55 * math.exp(-((hour_float + 1.0) ** 2) / 10)
    afternoon_dip = -25 * math.exp(-((hour_float - 15.0) ** 2) / 12)
    return max(15.0, 95 + morning + night + night2 + afternoon_dip + rng.gauss(0, 4))


class IndoorState:
    def __init__(self, pm25=45.0, co2=550.0, temp=25.0, hum=52.0):
        self.pm25, self.co2, self.temp, self.hum = pm25, co2, temp, hum
        self.window_open_left = 0.0  # minutes the window stays open

    def occupied(self, hour_float):
        # asleep / studying in the room at night and in the evening, mostly out during the day
        return hour_float >= 21 or hour_float < 8 or 17 <= hour_float < 21

    def step(self, dt_min, hour_float, outdoor_pm, rng=random):
        """Advance the room by dt_min minutes."""
        # window events: more likely when the room is stuffy
        if self.window_open_left <= 0:
            p = (1 / 240) if self.co2 < 1100 else (1 / 60)
            if rng.random() < p * dt_min:
                self.window_open_left = rng.uniform(8, 18)
        else:
            self.window_open_left -= dt_min
        window = self.window_open_left > 0

        # PM2.5: relax toward a fraction of outdoor (more leakage with the window open)
        target_pm = outdoor_pm * (0.85 if window else 0.45)
        k_pm = 1 - math.exp(-dt_min / (8 if window else 40))
        self.pm25 += (target_pm - self.pm25) * k_pm + rng.gauss(0, 0.6) * math.sqrt(dt_min)
        self.pm25 = max(3.0, self.pm25)

        # CO2: people add it, ventilation removes it
        if window:
            k = 1 - math.exp(-dt_min / 7)
            self.co2 += (440 - self.co2) * k
        else:
            if self.occupied(hour_float):
                self.co2 += 5.5 * dt_min
            else:
                self.co2 += (470 - self.co2) * (1 - math.exp(-dt_min / 120))
        self.co2 = min(2400.0, max(420.0, self.co2 + rng.gauss(0, 4) * math.sqrt(dt_min)))

        # temperature / humidity drift slowly with the time of day
        target_t = 25 + 4 * math.sin((hour_float - 9) / 24 * 2 * math.pi)
        self.temp += (target_t - self.temp) * (1 - math.exp(-dt_min / 90)) + rng.gauss(0, 0.04) * math.sqrt(dt_min)
        target_h = 55 - 8 * math.sin((hour_float - 9) / 24 * 2 * math.pi) + (4 if window else 0)
        self.hum += (target_h - self.hum) * (1 - math.exp(-dt_min / 120)) + rng.gauss(0, 0.1) * math.sqrt(dt_min)
        self.hum = min(85.0, max(25.0, self.hum))

    def reading(self):
        return {
            "pm25": round(self.pm25, 1),
            "co2": round(self.co2),
            "temp": round(self.temp, 1),
            "hum": round(self.hum, 1),
        }
