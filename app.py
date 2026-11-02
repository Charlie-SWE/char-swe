import multiprocessing
import sys
import threading

from nicegui import app, ui
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
    reset_database,
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
    """Fill/refresh the database without blocking the app."""

    def work():
        print(
            "[DATA] Updating game data in the background..."
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


def is_first_process():
    """False in the worker processes NiceGUI's auto-reload starts.

    They get the same command-line arguments, so without this
    --reset-db would also run every time the app reloads. A worker
    first loads this file as "__mp_main__" (before it knows its
    parent), then later as "__main__" (when it does), so both
    checks are needed.
    """
    return (
        __name__ == "__main__"
        and multiprocessing.parent_process() is None
    )


def main():
    if "--reset-db" in sys.argv[1:] and is_first_process():
        print("[DATA] --reset-db: wiping the database...")
        reset_database()

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
    ui.run(favicon="favicon.svg")


if __name__ in {"__main__", "__mp_main__"}:
    main()
