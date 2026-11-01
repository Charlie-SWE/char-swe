from nicegui import ui
import sqlite3
from pages import (
    landing,
    calendar,
    settings,
    chat,
    view_data,
    weather,
)

conn = sqlite3.connect("data/gaffer.db")
cursor = conn.cursor()


def getTeams():
    cursor.execute("""SELECT team_name FROM teams""")
    res = cursor.fetchall()
    result = []
    for x in res:
        result.insert(x)


def main():
    landing.init()  # layout now handeled by src/components/Layout.py
    calendar.init()
    settings.init()
    chat.init()
    view_data.init()
    weather.init()
    ui.run(favicon="favicon.svg")


if __name__ in {"__main__", "__mp_main__"}:
    main()
