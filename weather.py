import requests
from datetime import date

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = (
    "https://geocoding-api.open-meteo.com/v1/search"
)


def main():
    city = "Kent"
    state = "Ohio"
    day = date.today()

    print_weather(city, state, day)
    return


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


def print_weather(city, state, day):
    coords = city_to_coordinates(city, state)
    lat = coords["latitude"]
    lon = coords["longitude"]

    response = requests.get(
        FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": day.isoformat(),
            "end_date": day.isoformat(),
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "auto",
        },
        timeout=10,
    )
    print(response.json())


if __name__ == "__main__":
    main()
