# Hyperlocal Air Quality Monitor — software layer

Django backend + Next.js dashboard + Gemini chatbot. Indoor data is **simulated** until the ESP32 node arrives;
outdoor data comes from the free Open-Meteo API (no key needed).

```
simulate_live.py / ESP32  --POST /api/readings/-->  Django (SQLite)  <--GET /api/status/--  Next.js dashboard
Open-Meteo API  --every 20 min-->  Django                              rule engine + forecast + chatbot
```

## 1. Run the backend (Python 3.10+)

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo --hours 72 --clear     # 3 days of simulated history
python manage.py runserver 0.0.0.0:8000
```

## 2. Start the live simulator (second terminal)

```bash
cd backend
python simulate_live.py                      # one reading every 30 s, like the real node
python simulate_live.py --interval 5 --speed 6   # faster, so graphs visibly move during the demo
```

## 3. Run the dashboard (Node 20+, third terminal)

```bash
cd frontend
npm install
npm run dev          # open http://localhost:3000
```

If the backend is on another machine: `NEXT_PUBLIC_API_URL=http://<ip>:8000 npm run dev`

## 4. Turn on the Gemini chatbot (free)

1. Get a free key at https://aistudio.google.com/apikey
2. Set it before starting the backend:
   - Windows (PowerShell): `$env:GEMINI_API_KEY="your-key"`
   - Mac/Linux: `export GEMINI_API_KEY=your-key`
3. Optional: `GEMINI_MODEL` (default `gemini-2.5-flash`). If that model name is retired or the free quota is hit,
   the chatbot automatically falls back to a built-in summary, so the demo never shows an error.
   If the answer label says "built-in summary", Gemini was not used.

## What is real and what is simulated

| Item | Status |
|---|---|
| Outdoor PM2.5 / AQI | Real, from Open-Meteo (modelled, city-level) |
| Indoor PM2.5, CO2, temp, humidity | **Simulated** until the sensor arrives. Dashboard shows a "DEMO DATA" badge |
| Rule engine (open window / keep closed) | Real logic, working on the data above |
| Forecast | Simple linear trend. Do **not** train the ANN on simulated data |
| Chatbot | Real, answers only from the data it is given |

Say this openly in the presentation: "software layer complete, running on a simulated indoor feed; the real ESP32 node replaces it next week."

## Switching to the real hardware (next week)

1. Stop `simulate_live.py`.
2. Flash the ESP32 firmware, posting JSON to `http://<laptop-ip>:8000/api/readings/` with header `X-API-Key: demo-key`:
   `{"node_id":1,"pm25":84,"co2":1130,"temp":29.4,"hum":56}` (omit `source`, it defaults to `sensor`).
3. Optionally delete simulated rows: `python manage.py shell -c "from monitor.models import *; Reading.objects.filter(source='simulated').delete()"`
4. The dashboard badge switches to "LIVE SENSOR DATA" automatically.
5. Log real data for a week or two, then train the ANN offline and compare it against the linear baseline.

## API

| Endpoint | Purpose |
|---|---|
| `POST /api/readings/` | Device posts a reading (needs `X-API-Key`) |
| `GET /api/readings/?hours=24` | History for the charts |
| `GET /api/status/` | Latest indoor + outdoor, level, advice, forecast |
| `POST /api/chat/` | `{"message": "..."}` returns `{"reply": "...", "engine": "gemini"|"template"}` |

Change the key with `AQ_API_KEY`, and the location with `OUTDOOR_LAT` / `OUTDOOR_LON` (default Greater Noida).
Do not commit real keys to a public GitHub repo.
