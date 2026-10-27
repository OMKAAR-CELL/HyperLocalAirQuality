import json
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt

from . import chat, rules
from .forecast import forecast
from .models import OutdoorReading, Reading
from .outdoor import latest_outdoor


def _body(request):
    try:
        return json.loads(request.body or b"{}")
    except ValueError:
        return None


def build_status():
    """Everything the dashboard and chatbot need, in one dict."""
    latest = Reading.objects.order_by("-created_at").first()
    indoor = latest.as_dict() if latest else None
    out_row, stale = latest_outdoor()
    outdoor = out_row.as_dict() if out_row else None
    recent = list(Reading.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=6)).order_by("created_at"))
    return {
        "indoor": indoor,
        "indoor_source": indoor["source"] if indoor else None,
        "outdoor": outdoor,
        "outdoor_stale": stale,
        "level": rules.level_for(indoor),
        "advice": rules.advice_for(indoor, outdoor),
        "forecast": forecast(recent),
        "server_time": timezone.now().isoformat(),
    }


@csrf_exempt
def readings(request):
    if request.method == "POST":
        if request.headers.get("X-API-Key") != settings.API_KEY:
            return JsonResponse({"error": "invalid API key"}, status=401)
        data = _body(request)
        if data is None:
            return JsonResponse({"error": "invalid JSON"}, status=400)
        try:
            row = Reading(
                node_id=int(data.get("node_id", 1)),
                pm25=float(data["pm25"]),
                co2=float(data["co2"]),
                temp=float(data["temp"]),
                hum=float(data["hum"]),
                source="simulated" if data.get("source") == "simulated" else "sensor",
            )
        except (KeyError, TypeError, ValueError) as exc:
            return JsonResponse({"error": f"bad field: {exc}"}, status=400)
        # Only simulated rows may carry their own timestamp (used for seeding history).
        if row.source == "simulated" and data.get("ts"):
            ts = parse_datetime(data["ts"])
            if ts:
                row.created_at = ts
        row.save()
        return JsonResponse({"ok": True, "id": row.id}, status=201)

    hours = min(int(request.GET.get("hours", 24)), 24 * 14)
    qs = Reading.objects.filter(created_at__gte=timezone.now() - timedelta(hours=hours))
    outs = OutdoorReading.objects.filter(created_at__gte=timezone.now() - timedelta(hours=hours))
    return JsonResponse({
        "readings": [r.as_dict() for r in qs],
        "outdoor": [o.as_dict() for o in outs],
    })


def status(request):
    return JsonResponse(build_status())


@csrf_exempt
def chat_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    data = _body(request) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "empty message"}, status=400)
    reply, engine = chat.answer(message[:500], build_status())
    return JsonResponse({"reply": reply, "engine": engine})
