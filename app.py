import threading

from nicegui import app, ui, core
import sqlite3
from pages import (
    landing,
    calendar,
    settings,
    chat,
    view_data,
    weather,
)
from src.components.Scrape import (
    fill_database,
    prepare_database,
)

conn = sqlite3.connect("data/gaffer.db")
cursor = conn.cursor()


def getTeams():
    cursor.execute("""SELECT team_name FROM teams""")
    res = cursor.fetchall()
    result = []
    for x in res:
        result.insert(x)


def download_in_background():
    """First run: fill the database without blocking the app."""

    def work():
        print(
            "[DATA] Game data not downloaded yet."
            " Downloading the season in the background..."
        )
        try:
            fill_database()
        except Exception as exc:
            print(
                f"[DATA] Download stopped ({exc});"
                " it will continue next time the app starts."
            )

    threading.Thread(
        target=work, daemon=True, name="season-download"
    ).start()


def main():
    if prepare_database():
        # on_startup only fires in the process that serves
        # pages, so this runs once even with auto-reload on.
        app.on_startup(download_in_background)

    landing.init()  # layout now handeled by src/components/Layout.py
    calendar.init()
    settings.init()
    chat.init()
    view_data.init()
    weather.init()
    app.add_static_files('/assets', 'assets')
    core.app.config.socket_io_js_transports = ["polling"]
    ui.run(favicon="favicon.svg")


if __name__ in {"__main__", "__mp_main__"}:
    main()
