"""Chatbot: Gemini (free tier) answers from the live data; falls back to a template summary."""
import json
import logging

import requests
from django.conf import settings

log = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = (
    "You are the assistant for a room-level air quality monitor in a college hostel in Greater Noida. "
    "Answer ONLY from the JSON data provided. Never invent numbers. If something is missing, say so. "
    "Keep replies short (2-4 sentences) in plain, friendly English. "
    "If data_source for indoor is 'simulated', mention once that indoor values are demo data. "
    "Thresholds: CO2 under 800 ppm is good, 800-1200 is stuffy, above 1200 is poor. "
    "PM2.5 under 60 ug/m3 is good, 60-120 is unhealthy for sensitive people, above 120 is unhealthy."
)


def template_summary(ctx):
    """Always-available fallback, built only from the data."""
    indoor, outdoor = ctx.get("indoor"), ctx.get("outdoor")
    if not indoor:
        return "I don't have any indoor readings yet."
    parts = [
        f"Indoors, CO2 is {indoor['co2']} ppm and PM2.5 is {indoor['pm25']} ug/m3 "
        f"(status: {ctx['level']})."
    ]
    if outdoor:
        parts.append(f"Outside, PM2.5 is {outdoor['pm25']} ug/m3 (AQI {outdoor['aqi']}).")
    parts.append(ctx["advice"])
    fc = ctx.get("forecast")
    if fc:
        parts.append(
            f"In about {fc['minutes_ahead']} minutes CO2 is expected to be around {fc['co2']} ppm "
            f"({fc['co2_trend']}) and PM2.5 around {fc['pm25']} ug/m3 ({fc['pm25_trend']})."
        )
    if ctx.get("indoor_source") == "simulated":
        parts.append("Note: indoor values are demo data until the sensor node is connected.")
    return " ".join(parts)


def answer(message, ctx):
    """Returns (reply_text, engine) where engine is 'gemini' or 'template'."""
    key = settings.GEMINI_API_KEY
    if not key:
        return template_summary(ctx), "template"
    try:
        body = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{
                "role": "user",
                "parts": [{"text": "DATA:\n" + json.dumps(ctx, default=str) + "\n\nQUESTION: " + message}],
            }],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 300},
        }
        resp = requests.post(
            GEMINI_URL.format(model=settings.GEMINI_MODEL),
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json=body,
            timeout=12,
        )
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if text:
            return text, "gemini"
    except Exception as exc:
        log.warning("Gemini call failed: %s", exc)
    return template_summary(ctx), "template"
