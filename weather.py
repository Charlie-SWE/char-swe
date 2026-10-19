import requests
from datetime import date, timedelta

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = (
    "https://geocoding-api.open-meteo.com/v1/search"
)
ARCHIVE_URL = "https://archive-api.open-meteo/v1/archive"


def main():
    city = "Kent"
    state = "Ohio"
    start_day = date.today()
    end_day = date.today() + timedelta(days=10)

    weather = get_weather(city, state, start_day, end_day)
    return


# Picks the correct URL based on the day
def pick_url(start_day, end_day):
    today = date.today()

    # Makes sure end date is not more than 16 days ahead
    if end_day > today + timedelta(days=16):
        raise ValueError(
            "The forecast only gives up to 16 days in the future"
        )

    # Archive URL starts at five day delay
    if end_day < (today - timedelta(days=5)):
        return ARCHIVE_URL
    return FORECAST_URL


def city_to_coordinates(city, state):
    # Asks the API where the zip code is
    response = requests.get(
        GEOCODE_URL,
        params={
            "name": city,
            "countryCode": "US",
        },
        timeout=10,
    )

    # If there is an error, tell me
    response.raise_for_status()

    # Iterates through all states with city name
    for r in response.json().get("results", []):

        # admin1 is the state
        r_state = r.get("admin1")

        # Return if we find the state
        if r_state == state:
            long_lat_dict = {
                "latitude": r["latitude"],
                "longitude": r["longitude"],
            }
            return long_lat_dict

    # Raise an error if we don't find the city+state combo
    raise ValueError(
        f"No location found for {city}, {state}"
    )


def get_weather(city, state, start_day, end_day=None):
    # If end_day not selected, just pulls the start day data
    if end_day == None:
        end_day = start_day
    if end_day < start_day:
        raise ValueError(
            "end_day must be the same as or after start_day"
        )

    coords = city_to_coordinates(city, state)
    lat = coords["latitude"]
    lon = coords["longitude"]

    url = pick_url(start_day, end_day)

    response = requests.get(
        url,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start_day.isoformat(),
            "end_date": end_day.isoformat(),
            # Pulls like all of the weather stuff
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "auto",
        },
        timeout=10,
    )

    # Catches errors
    response.raise_for_status()

    r = response.json()

    weather = []
    daily = r["daily"]
    day_count = len(daily["time"])
    for i in range(day_count):
        day_dict = {
            "date": daily["time"][i],
            "weather_code": daily["weather_code"][i],
            "min_temp": daily["temperature_2m_min"][i],
            "max_temp": daily["temperature_2m_max"][i],
            "precipitation": daily["precipitation_sum"][i],
            "wind_speed": daily["wind_speed_10m_max"][i],
        }
        weather.append(day_dict)

    all_info_dict = {
        "latitude": r["latitude"],
        "longitude": r["longitude"],
        "timezone": r["timezone"],
        "elevation": r["elevation"],
        "weather": weather,
    }

    return all_info_dict


if __name__ == "__main__":
    main()
