import threading
from nicegui import app, ui
from src.components.Colors import load_css

from pages import (
    landing,
    calendar,
    settings,
    chat,
    view_data,
    weather,
    xgboost,
)


def main():
    # Imports all of the CSS
    load_css()

    # Loads all of the pages
    landing.init()
    calendar.init()
    settings.init()
    chat.init()
    view_data.init()
    weather.init()
    app.add_static_files("/assets", "assets")

    # Loads the favicon
    xgboost.init()
    ui.run(favicon="favicon.svg")


if __name__ in {"__main__", "__mp_main__"}:
    main()
