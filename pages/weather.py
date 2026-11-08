from datetime import date

from nicegui import run, ui

from src.components.Colors import PrimaryDarkHex, PrimaryLightHex, SecondaryDarkHex
from src.components.Layout import frame, page_body, page_header
from src.services.weather import get_weather

def pretty(key: str) -> str:
    return key.replace("_", " ").title()


def coord(value) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def init():
    @ui.page("/weather")
    def weather_page():
        frame("weather")

        with page_body():
            page_header("CONDITIONS", "Weather", "Conditions for match days, past or upcoming.")

            # Inputs
            with ui.column().classes("card w-full p-5 gap-4"):
                ui.label("Location & dates").classes("font-display text-lg font-bold").style(
                    f"color:{SecondaryDarkHex}"
                )
                with ui.element("div").classes("w-full grid gap-3 items-end").style(
                    "grid-template-columns:repeat(auto-fit,minmax(180px,1fr))"
                ):
                    city = ui.input("City", value="Kent").props("outlined dense")
                    state = ui.input("State", value="Ohio").props("outlined dense")
                    start = ui.input("Start", value=date.today().isoformat()).props(
                        "outlined dense type=date stack-label"
                    )
                    end = ui.input("End (optional)").props("outlined dense type=date stack-label clearable")
                    fetch_button = ui.button("Get weather", icon="cloud").props("unelevated no-caps").style(
                        f"background:{PrimaryLightHex} !important; color:{SecondaryDarkHex};"
                        "font-weight:700; border-radius:10px; height:40px"
                    )

            # Results
            with ui.column().classes("card w-full p-0 gap-0 overflow-hidden"):
                with ui.row().classes("w-full items-center justify-between gap-3 px-5 py-4").style(
                    "border-bottom:1px solid #E3E6EC"
                ):
                    ui.label("Conditions").classes("font-display text-lg font-bold").style(
                        f"color:{SecondaryDarkHex}"
                    )
                    location_chip = ui.row().classes("items-center gap-1 text-xs px-2 py-1 rounded-full").style(
                        f"background:#EEF2F9; color:{PrimaryDarkHex}"
                    )
                    location_chip.set_visibility(False)
                results = ui.column().classes("w-full gap-0")

        def empty_state(icon: str, text: str):
            with results:
                with ui.column().classes("w-full items-center justify-center gap-2 py-16"):
                    ui.icon(icon).style("color:#B9C4D8; font-size:36px")
                    ui.label(text).classes("text-sm").style("color:#7A849A")

        async def fetch():
            if not (city.value or "").strip() or not (state.value or "").strip():
                ui.notify("Enter a city and a state.", type="warning")
                return
            if not start.value:
                ui.notify("Pick a start date.", type="warning")
                return
            start_day = date.fromisoformat(start.value)
            end_day = date.fromisoformat(end.value) if end.value else None
            if end_day and end_day < start_day:
                ui.notify("End date must be on or after the start date.", type="warning")
                return

            results.clear()
            location_chip.set_visibility(False)
            fetch_button.props("loading")
            try:
                data = await run.io_bound(get_weather, city.value, state.value, start_day, end_day)
            except Exception as e:
                ui.notify(str(e), type="negative")
                empty_state("cloud_off", "Couldn't load weather data.")
                return
            finally:
                fetch_button.props(remove="loading")

            rows = data.get("weather") or []
            location_chip.clear()
            with location_chip:
                ui.icon("place").style("font-size:14px")
                ui.label(
                    f"{coord(data.get('latitude'))}, {coord(data.get('longitude'))} · {data.get('timezone', '')}"
                ).classes("font-semibold")
            location_chip.set_visibility(True)

            if not rows:
                empty_state("cloud_off", "No weather data for these dates.")
                return

            with results:
                ui.table(
                    columns=[
                        {"name": k, "label": pretty(k), "field": k, "align": "left"}
                        for k in rows[0]
                    ],
                    rows=rows,
                ).props("flat").classes("data-table w-full")

        fetch_button.on_click(fetch)
        empty_state("wb_sunny", "Choose a location and dates, then click Get weather.")
