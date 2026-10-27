
"""Chatbot: Groq answers from live air-quality data."""
import json
import logging

import requests
from django.conf import settings

log = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are the assistant for a room-level air quality monitor "
    "in a college hostel in Greater Noida. "
    "Answer ONLY from the JSON data provided. Never invent numbers. "
    "If something is missing, say so. "
    "Keep replies short (2-4 sentences) in plain, friendly English. "
    "If indoor_source is 'simulated', mention that indoor values "
    "are demo data. "
    "CO2 under 800 ppm is good, 800-1200 is stuffy, "
    "above 1200 is poor. "
    "PM2.5 under 60 ug/m3 is good, 60-120 is unhealthy "
    "for sensitive people, above 120 is unhealthy."
)


def template_summary(ctx):
    """Fallback response built from available data."""
    indoor, outdoor = ctx.get("indoor"), ctx.get("outdoor")

    if not indoor:
        return "I don't have any indoor readings yet."

    parts = [
        f"Indoors, CO2 is {indoor['co2']} ppm and "
        f"PM2.5 is {indoor['pm25']} ug/m3 "
        f"(status: {ctx['level']})."
    ]

    if outdoor:
        parts.append(
            f"Outside, PM2.5 is {outdoor['pm25']} ug/m3 "
            f"(AQI {outdoor['aqi']})."
        )

    parts.append(ctx["advice"])

    fc = ctx.get("forecast")
    if fc:
        parts.append(
            f"In about {fc['minutes_ahead']} minutes CO2 "
            f"is expected to be around {fc['co2']} ppm "
            f"({fc['co2_trend']}) and PM2.5 around "
            f"{fc['pm25']} ug/m3 ({fc['pm25_trend']})."
        )

    if ctx.get("indoor_source") == "simulated":
        parts.append(
            "Note: indoor values are demo data until "
            "the sensor node is connected."
        )

    return " ".join(parts)


def answer(message, ctx):
    """Returns (reply_text, engine): groq or template."""
    key = getattr(settings, "GROQ_API_KEY", "")
    model = getattr(
    settings,
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
)

    if not key:
        log.warning("GROQ_API_KEY is missing; using template.")
        return template_summary(ctx), "template"

    try:
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "DATA:\n"
                        + json.dumps(ctx, default=str)
                        + "\n\nQUESTION: "
                        + message
                    ),
                },
            ],
            "temperature": 0.3,
            "max_tokens": 300,
        }

        resp = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=20,
        )
        resp.raise_for_status()

        result = resp.json()
        reply = (
            result["choices"][0]["message"]["content"] or ""
        ).strip()

        if reply:
            return reply, "groq"

        log.warning("Groq returned an empty response.")

    except requests.RequestException:
        log.exception("Groq API request failed.")
    except (KeyError, IndexError, TypeError, ValueError):
        log.exception("Unexpected Groq API response.")

    return template_summary(ctx), "template"
