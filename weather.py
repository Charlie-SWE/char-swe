import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = (
    "https://geocoding-api.open-meteo.com/v1/search"
)


def main():
    latitude = "41.15717138785759"
    longitude = "-81.32781621901985"
    zipcode = "44242"

    # print_weather(latitude, longitude)
    coords = city_to_coordinates("Athens", "Georgia")
    print(coords["latitude"])
    print(coords["longitude"])
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

    raise ValueError(
        f"No location found for {city}, {state}"
    )

    # response.raise_for_status()
    # results = response.json().get("results")

    # Makes sure we actually got a result
    # if not results:
    #    raise ValueError(
    #        f"No location found for zip code {zip_code}"
    #    )

    # Pulls out the actual result
    # actual_result = results[0]

    # Creates a dictionary of the longitude and latitude


def print_weather(latitude, longitude):
    response = requests.get(
        FORECAST_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
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
