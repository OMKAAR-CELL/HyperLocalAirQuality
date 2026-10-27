"""Live simulator: POSTs fake-but-plausible readings to the SAME endpoint the ESP32 will use.

Run:   python simulate_live.py                       (one reading every 30 s, like the real node)
Demo:  python simulate_live.py --interval 5 --speed 6  (faster, so graphs visibly move)

Next week: stop this script and flash the ESP32. Nothing else changes.
"""
import argparse
import random
import time
from datetime import datetime, timedelta, timezone

import requests

from simmodel import IndoorState, outdoor_pm25

p = argparse.ArgumentParser()
p.add_argument("--url", default="http://localhost:8000")
p.add_argument("--key", default="demo-key")
p.add_argument("--interval", type=float, default=30, help="real seconds between posts")
p.add_argument("--speed", type=float, default=1, help="simulated minutes per real minute")
a = p.parse_args()

headers = {"X-API-Key": a.key, "Content-Type": "application/json"}
state = IndoorState()

try:
    st = requests.get(f"{a.url}/api/status/", timeout=10).json()
    if st.get("indoor"):
        i = st["indoor"]
        state = IndoorState(pm25=i["pm25"], co2=i["co2"], temp=i["temp"], hum=i["hum"])
        print("Continuing from last stored reading:", i)
except Exception as e:
    print("Could not read status (is the backend running?):", e)

sim_clock = datetime.now(timezone.utc)
dt_min = a.interval * a.speed / 60

print(f"Posting to {a.url}/api/readings/ every {a.interval}s (speed x{a.speed}). Ctrl+C to stop.")
while True:
    try:
        local = sim_clock + timedelta(hours=5, minutes=30)
        hour = local.hour + local.minute / 60

        # follow the REAL outdoor value when the backend has one, otherwise the synthetic curve
        out_pm = None
        try:
            st = requests.get(f"{a.url}/api/status/", timeout=10).json()
            if st.get("outdoor") and st["outdoor"]["source"] != "simulated":
                out_pm = st["outdoor"]["pm25"]
        except Exception:
            pass
        if out_pm is None:
            out_pm = outdoor_pm25(hour)

        state.step(dt_min, hour, out_pm)
        payload = {"node_id": 1, "source": "simulated", **state.reading()}
        if a.speed != 1:  # keep the simulated clock consistent with the sped-up data
            payload["ts"] = sim_clock.isoformat()
        r = requests.post(f"{a.url}/api/readings/", json=payload, headers=headers, timeout=10)
        print(r.status_code, payload)
        sim_clock += timedelta(minutes=dt_min)
    except KeyboardInterrupt:
        break
    except Exception as e:
        print("post failed:", e)
    time.sleep(a.interval)
