"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Chart from "./Chart";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const COLORS = { green: "var(--green)", yellow: "var(--yellow)", red: "var(--red)", unknown: "var(--line)" };
const LEVEL_TEXT = { green: "Good", yellow: "Stuffy", red: "Poor", unknown: "No data" };
const SUGGESTIONS = [
  "Is the air safe right now?",
  "Should I open the window?",
  "What will CO2 be in an hour?",
  "Summarise everything",
];

export default function Home() {
  const [status, setStatus] = useState(null);
  const [hist, setHist] = useState({ readings: [], outdoor: [] });
  const [hours, setHours] = useState(24);
  const [error, setError] = useState("");
  const [msgs, setMsgs] = useState([
    { who: "b", text: "Hi! Ask me about the air in this room, for example: Should I open the window?" },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  const loadStatus = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/status/`, { cache: "no-store" });
      setStatus(await r.json());
      setError("");
    } catch {
      setError("Cannot reach the backend. Is it running on " + API + "?");
    }
  }, []);

  const loadHist = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/readings/?hours=${hours}`, { cache: "no-store" });
      setHist(await r.json());
    } catch {}
  }, [hours]);

  useEffect(() => {
    loadStatus();
    const id = setInterval(loadStatus, 10000);
    return () => clearInterval(id);
  }, [loadStatus]);

  useEffect(() => {
    loadHist();
    const id = setInterval(loadHist, 30000);
    return () => clearInterval(id);
  }, [loadHist]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  async function send(text) {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setInput("");
    setMsgs((m) => [...m, { who: "u", text: q }]);
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: q }),
      });
      const d = await r.json();
      setMsgs((m) => [...m, { who: "b", text: d.reply || d.error || "No reply.", engine: d.engine }]);
    } catch {
      setMsgs((m) => [...m, { who: "b", text: "Could not reach the backend." }]);
    }
    setBusy(false);
  }

  const ind = status?.indoor;
  const out = status?.outdoor;
  const fc = status?.forecast;
  const level = status?.level || "unknown";
  const demo = status?.indoor_source === "simulated";
  const outdoorLabel = !out
    ? "no data"
    : out.source === "simulated"
    ? "fallback demo value (API unreachable)"
    : status.outdoor_stale
    ? "Open-Meteo (stale)"
    : "Open-Meteo (city-level model)";

  const toPts = (rows, key) => rows.map((r) => ({ t: new Date(r.time).getTime(), v: r[key] }));

  return (
    <div className="wrap">
      <header>
        <div>
          <h1>Hyperlocal Air Quality Monitor</h1>
          <div className="sub">Room-level CO2 and PM2.5 with outdoor comparison, forecast and assistant</div>
        </div>
        {status && (
          <span className={`badge ${demo ? "demo" : "live"}`}>
            {demo ? "DEMO DATA · sensor node arriving" : "LIVE SENSOR DATA"}
          </span>
        )}
      </header>

      {error && <div className="err">{error}</div>}

      <section className="card status" style={{ "--c": COLORS[level] }}>
        <div className="lvl">{LEVEL_TEXT[level]}</div>
        <div className="adv">{status?.advice || "Loading..."}</div>
      </section>

      <section className="grid">
        <div className="card metric">
          <h2>Indoor CO2</h2>
          <div className="val">{ind ? ind.co2 : "--"}<span className="unit">ppm</span></div>
          <div className="note">Good under 800, poor above 1200</div>
        </div>
        <div className="card metric">
          <h2>Indoor PM2.5</h2>
          <div className="val">{ind ? ind.pm25 : "--"}<span className="unit">µg/m³</span></div>
          <div className="note">Good under 60, poor above 120</div>
        </div>
        <div className="card metric">
          <h2>Temp / Humidity</h2>
          <div className="val">{ind ? `${ind.temp}°` : "--"}<span className="unit">{ind ? `${ind.hum}% RH` : ""}</span></div>
          <div className="note">Inside the room</div>
        </div>
        <div className="card metric">
          <h2>Outdoor PM2.5</h2>
          <div className="val">{out ? out.pm25 : "--"}<span className="unit">µg/m³</span></div>
          <div className="note">{out && out.aqi != null ? `AQI ${out.aqi} · ` : ""}{outdoorLabel}</div>
        </div>
      </section>

      <section className="two">
        <div className="card">
          <div className="chart-head">
            <h2 style={{ margin: 0 }}>Indoor CO2 (ppm)</h2>
            <div className="range">
              {[6, 24, 72].map((h) => (
                <button key={h} className={hours === h ? "on" : ""} onClick={() => setHours(h)}>{h}h</button>
              ))}
            </div>
          </div>
          <Chart unit="ppm"
            series={[{ name: "CO2", color: "var(--accent)", points: toPts(hist.readings, "co2") }]}
            threshold={{ value: 1200, label: "poor: 1200" }} />
        </div>
        <div className="card">
          <div className="chart-head"><h2 style={{ margin: 0 }}>PM2.5: indoor vs outdoor (µg/m³)</h2></div>
          <Chart unit="ug/m3"
            series={[
              { name: "Indoor", color: "var(--accent)", points: toPts(hist.readings, "pm25") },
              { name: "Outdoor", color: "var(--yellow)", points: toPts(hist.outdoor, "pm25") },
            ]}
            threshold={{ value: 60, label: "limit: 60" }} />
          <div className="legend">
            <span><i style={{ background: "var(--accent)" }} />Indoor</span>
            <span><i style={{ background: "var(--yellow)" }} />Outdoor</span>
          </div>
        </div>
      </section>

      <section className="two">
        <div className="card">
          <h2>Forecast · next {fc?.minutes_ahead ?? 60} min</h2>
          {fc ? (
            <div className="fc">
              <div><div className="big">{fc.co2} ppm</div><div className="t">CO2 · {fc.co2_trend}</div></div>
              <div><div className="big">{fc.pm25} µg/m³</div><div className="t">PM2.5 · {fc.pm25_trend}</div></div>
            </div>
          ) : (
            <div className="sub">Collecting data...</div>
          )}
          <div className="sub" style={{ marginTop: 10 }}>
            Method: {fc?.method || "linear trend"}. A neural network will replace this once real sensor data is logged.
          </div>
        </div>

        <div className="card chat">
          <h2>Ask the assistant</h2>
          <div className="msgs">
            {msgs.map((m, i) => (
              <div key={i} className={`m ${m.who}`}>
                {m.text}
                {m.engine && <small>answered by {m.engine === "gemini" ? "Gemini" : "built-in summary"}</small>}
              </div>
            ))}
            {busy && <div className="m b">Thinking...</div>}
            <div ref={endRef} />
          </div>
          <div className="chips">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)} disabled={busy}>{s}</button>
            ))}
          </div>
          <form className="row" onSubmit={(e) => { e.preventDefault(); send(); }}>
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about the air quality..." />
            <button disabled={busy || !input.trim()}>Send</button>
          </form>
        </div>
      </section>

      <footer>
        Indoor: ESP32 node (PMS5003, MH-Z19B, BME280){demo ? ", currently simulated for the demo" : ""} · Outdoor: public API · Updated{" "}
        {status ? new Date(status.server_time).toLocaleTimeString() : "--"}
      </footer>
    </div>
  );
}
