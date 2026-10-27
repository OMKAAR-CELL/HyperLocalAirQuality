"""Fill the database with N hours of simulated history so graphs and the forecast are not empty.

Usage: python manage.py seed_demo --hours 72 --clear
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from monitor.models import OutdoorReading, Reading
from simmodel import IndoorState, outdoor_pm25


class Command(BaseCommand):
    help = "Seed simulated indoor + outdoor history (labelled source='simulated')."

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=72)
        parser.add_argument("--step", type=int, default=5, help="minutes between readings")
        parser.add_argument("--clear", action="store_true", help="delete existing simulated rows first")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **o):
        rng = random.Random(o["seed"])
        if o["clear"]:
            Reading.objects.filter(source="simulated").delete()
            OutdoorReading.objects.filter(source="simulated").delete()

        end = timezone.now()
        start = end - timedelta(hours=o["hours"])
        state = IndoorState()
        readings, outdoors = [], []
        t = start
        step = o["step"]
        n = 0
        while t <= end:
            local = t + timedelta(hours=5, minutes=30)  # IST for the daily pattern
            hour = local.hour + local.minute / 60
            out_pm = outdoor_pm25(hour, rng)
            state.step(step, hour, out_pm, rng)
            r = state.reading()
            readings.append(Reading(node_id=1, source="simulated", created_at=t, **r))
            if n % 6 == 0:  # outdoor sample every 30 minutes
                outdoors.append(OutdoorReading(
                    pm25=round(out_pm, 1), pm10=round(out_pm * 1.6, 1),
                    aqi=round(min(500, out_pm * 1.9)), source="simulated", created_at=t))
            t += timedelta(minutes=step)
            n += 1
        Reading.objects.bulk_create(readings)
        OutdoorReading.objects.bulk_create(outdoors)
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(readings)} indoor and {len(outdoors)} outdoor simulated rows."))
