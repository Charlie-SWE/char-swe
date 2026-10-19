from datetime import date, timedelta
import pytest
import src.services.weather as weather


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data

    def raise_for_status(self):
        pass


def fake_get(url, params=None, timeout=None):
    if url == weather.GEOCODE_URL:
        return FakeResponse(
            {
                "results": [
                    {
                        "admin1": "Georgia",
                        "latitude": 33.9,
                        "longitude": -83.4,
                    },
                    {
                        "admin1": "Ohio",
                        "latitude": 39.3,
                        "longitude": -82.1,
                    },
                ]
            }
        )
    return FakeResponse(
        {
            "latitude": 39.3,
            "longitude": -82.1,
            "timezone": "America/New_York",
            "elevation": 200,
            "daily": {
                "time": ["2026-10-18", "2026-10-19"],
                "weather_code": [3, 61],
                "temperature_2m_max": [61.7, 55.0],
                "temperature_2m_min": [31.5, 40.2],
                "precipitation_sum": [0.0, 0.3],
                "wind_speed_10m_max": [10.1, 14.5],
            },
        }
    )


def test_picks_right_state(monkeypatch):
    monkeypatch.setattr(weather.requests, "get", fake_get)
    coords = weather.city_to_coordinates("Athens", "Ohio")
    assert coords["latitude"] == 39.3


def test_get_weather_output(monkeypatch):
    monkeypatch.setattr(weather.requests, "get", fake_get)
    result = weather.get_weather(
        "Athens",
        "Ohio",
        date(2026, 10, 18),
        date(2026, 10, 19),
    )
    assert len(result["weather"]) == 2
    assert result["weather"][0]["max_temp"] == 61.7
    assert result["timezone"] == "America/New_York"


def test_end_before_start_raises():
    with pytest.raises(ValueError):
        weather.get_weather(
            "Kent",
            "Ohio",
            date(2026, 10, 19),
            date(2026, 10, 18),
        )


def test_pick_url():
    today = date.today()
    assert (
        weather.pick_url(today, today)
        == weather.FORECAST_URL
    )
    old = today - timedelta(days=365)
    assert weather.pick_url(old, old) == weather.ARCHIVE_URL
    with pytest.raises(ValueError):
        far = today + timedelta(days=30)
        weather.pick_url(far, far)
