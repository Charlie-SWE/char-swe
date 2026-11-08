import threading
from nicegui import app, ui
from pages import (
    landing,
    calendar,
    settings,
    chat,
    view_data,
    weather,
)


def main():
    landing.init()
    calendar.init()
    settings.init()
    chat.init()
    view_data.init()
    weather.init()
    app.add_static_files("/assets", "assets")
    ui.run(favicon="favicon.svg")


if __name__ in {"__main__", "__mp_main__"}:
    main()
