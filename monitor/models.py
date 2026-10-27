from django.db import models
from django.utils import timezone


class Reading(models.Model):
    """One indoor reading from the ESP32 node (or the simulator)."""

    SOURCES = [("sensor", "sensor"), ("simulated", "simulated")]

    node_id = models.IntegerField(default=1)
    pm25 = models.FloatField()
    co2 = models.FloatField()
    temp = models.FloatField()
    hum = models.FloatField()
    source = models.CharField(max_length=12, choices=SOURCES, default="sensor")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["created_at"]

    def as_dict(self):
        return {
            "node_id": self.node_id,
            "pm25": round(self.pm25, 1),
            "co2": round(self.co2),
            "temp": round(self.temp, 1),
            "hum": round(self.hum, 1),
            "source": self.source,
            "time": self.created_at.isoformat(),
        }


class OutdoorReading(models.Model):
    """Outdoor air quality pulled from a public API (or a labelled fallback)."""

    pm25 = models.FloatField()
    pm10 = models.FloatField(null=True, blank=True)
    aqi = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=32, default="open-meteo")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["created_at"]

    def as_dict(self):
        return {
            "pm25": round(self.pm25, 1),
            "pm10": None if self.pm10 is None else round(self.pm10, 1),
            "aqi": None if self.aqi is None else round(self.aqi),
            "source": self.source,
            "time": self.created_at.isoformat(),
        }
