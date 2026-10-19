from nicegui import ui, run
from datetime import date
from src.components.Layout import frame
from src.services.weather import get_weather


def init():
    @ui.page("/weather")
    def weather_page():
        frame()

        # Title
        ui.label("Weather").classes("text-4xl font-bold")

        # Input Fields
        city = ui.input("City", value="Kent")
        state = ui.input("State", value="Ohio")
        start = ui.input("Start").props("type=date")
        end = ui.input("End (optional)").props("type=date")
        results = ui.column()

        async def fetch():
            results.clear()
            try:
                start_day = date.fromisoformat(start.value)
                end_day = (
                    date.fromisoformat(end.value)
                    if end.value
                    else None
                )
                data = await run.io_bound(
                    get_weather,
                    city.value,
                    state.value,
                    start_day,
                    end_day,
                )
            except Exception as e:
                ui.notify(str(e), type="negative")
                return

            with results:
                ui.label(
                    f"{data['latitude']}, "
                    f"{data['longitude']} "
                    f"({data['timezone']})"
                )
                ui.table(
                    rows=data["weather"],
                    columns=[
                        {
                            "name": key,
                            "label": key,
                            "field": key,
                        }
                        for key in data["weather"][0]
                    ],
                )

        ui.button("Get Weather", on_click=fetch)
