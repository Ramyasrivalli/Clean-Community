"""Reusable OpenWeatherMap client and sanitation alert rules for the portal."""

from __future__ import annotations

import time
from typing import Any

import requests


class WeatherService:
    """Fetch and format current OpenWeatherMap data for template use."""

    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
    CACHE_SECONDS = 600

    def __init__(self, api_key: str | None) -> None:
        # Keep the key in the service instance so templates and routes never handle it.
        self.api_key = api_key
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def get_current_weather(self, city: str | None) -> dict[str, Any] | None:
        """Return safe, display-ready weather data, or None when it is unavailable."""
        normalized_city = (city or "").strip()
        if not normalized_city or not self.api_key:
            return None

        # A short per-city cache keeps page loads quick and limits API usage.
        cache_key = normalized_city.casefold()
        cached_weather = self._cache.get(cache_key)
        if cached_weather and time.monotonic() - cached_weather[0] < self.CACHE_SECONDS:
            return cached_weather[1]

        try:
            response = requests.get(
                self.BASE_URL,
                params={"q": normalized_city, "appid": self.api_key, "units": "metric"},
                timeout=5,
            )
            response.raise_for_status()
            weather_data = response.json()
            formatted_weather = self._format_weather(weather_data)
        except (requests.RequestException, ValueError, KeyError, TypeError, IndexError, AttributeError):
            # API/network errors must never prevent visitors from using the portal.
            return None

        self._cache[cache_key] = (time.monotonic(), formatted_weather)
        return formatted_weather

    @staticmethod
    def _format_weather(weather_data: dict[str, Any]) -> dict[str, Any]:
        """Reduce the API response to only the trusted fields the UI needs."""
        if not isinstance(weather_data, dict):
            raise ValueError("Weather API returned an unexpected response.")

        weather_entries = weather_data.get("weather")
        main_data = weather_data.get("main")
        primary_condition = weather_entries[0] if isinstance(weather_entries, list) and weather_entries else None
        if not isinstance(primary_condition, dict) or not isinstance(main_data, dict):
            raise ValueError("Weather API response is missing required weather details.")

        city = weather_data.get("name")
        condition_name = primary_condition.get("main")
        description = primary_condition.get("description")
        icon_code = primary_condition.get("icon")
        if not all(isinstance(value, str) and value for value in (city, condition_name, description, icon_code)):
            raise ValueError("Weather API response contains invalid weather details.")

        temperature = float(main_data["temp"])
        humidity = int(main_data["humidity"])
        wind_data = weather_data.get("wind", {})
        wind_speed = float(wind_data.get("speed", 0)) if isinstance(wind_data, dict) else 0

        return {
            "city": city,
            "temperature": round(temperature),
            "condition": description.capitalize(),
            "icon_url": f"https://openweathermap.org/img/wn/{icon_code}@2x.png",
            "humidity": humidity,
            "wind_speed": round(wind_speed, 1),
            "alerts": WeatherService._sanitation_alerts(
                condition_name, weather_data.get("rain"), temperature, humidity
            ),
        }

    @staticmethod
    def _sanitation_alerts(
        condition_name: str, rain_data: Any, temperature: float, humidity: int
    ) -> list[dict[str, str]]:
        """Create targeted hygiene guidance from the current weather conditions."""
        alerts: list[dict[str, str]] = []
        rain_conditions = {"rain", "drizzle", "thunderstorm"}

        # The Current Weather API signals rain through its condition and/or rain volume field.
        if condition_name.casefold() in rain_conditions or rain_data:
            alerts.append(
                {
                    "icon": "⚠",
                    "message": "Heavy rain may increase drainage and water stagnation issues.",
                }
            )
        if temperature > 38:
            alerts.append(
                {
                    "icon": "💧",
                    "message": "Drink enough clean water and avoid dehydration.",
                }
            )
        if humidity > 80:
            alerts.append(
                {
                    "icon": "🦟",
                    "message": "High humidity may increase mosquito breeding.",
                }
            )
        if condition_name.casefold() == "clear":
            alerts.append(
                {
                    "icon": "✅",
                    "message": "Good weather for community cleanliness activities.",
                }
            )
        return alerts
