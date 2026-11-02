import calendar
import sqlite3
from contextlib import closing
from datetime import date

from nicegui import ui
from src.components.Layout import frame
from src.components.Colors import (
    PrimaryDarkHex,
    PrimaryLightHex,
    SecondaryGrayHex,
    SecondaryLightHex,
    SecondaryYellowHex,
)
from src.services.games import (
    build_calendar_html,
    latest_game_month,
    shift_month,
    team_games_in_month,
)
from src.services.query_builder import DB_PATH, list_teams

DEFAULT_TEAM_NAME = "Kent State University"


def init():
    @ui.page("/calendar")
    def calendar_page():
        frame()
        today = date.today()

        css = f"""
                .calendar {{
                    width: 100%;
                    border-collapse: collapse;
                    text-align: center;
                    table-layout: fixed;
                }}

                .calendar th {{
                    background-color: {PrimaryDarkHex};
                    color: white;
                    padding: 12px;
                }}

                .calendar td {{
                    border: 1px solid {SecondaryLightHex};
                    padding: 8px 6px;
                    height: 90px;
                    vertical-align: top;
                }}

                .day-number {{
                    font-weight: bold;
                }}

                .today {{
                    background-color: {PrimaryLightHex};
                    outline: 3px solid {PrimaryDarkHex};
                    outline-offset: -3px;
                }}

                .today-tag {{
                    display: inline-block;
                    background-color: {PrimaryDarkHex};
                    color: white;
                    font-size: 0.7rem;
                    padding: 0 6px;
                    border-radius: 8px;
                }}

                .game {{
                    background-color: {SecondaryYellowHex}33;
                }}

                .past-game {{
                    background-color: #f1f1f1;
                    color: {SecondaryGrayHex};
                }}

                .past-game .event-dot {{
                    background-color: {SecondaryGrayHex};
                }}

                .game-info {{
                    font-size: 0.75rem;
                    margin-top: 4px;
                    overflow-wrap: anywhere;
                }}

                .event-dot {{
                    height: 8px;
                    width: 8px;
                    background-color: {SecondaryYellowHex};
                    border: 1px solid {PrimaryDarkHex};
                    border-radius: 50%;
                    display: inline-block;
                    vertical-align: middle;
                }}
        """

        ui.add_css(css)

        with closing(sqlite3.connect(DB_PATH)) as conn:
            teams = list_teams(conn)
        default_team = next(
            (
                team_id
                for team_id, team_name in teams.items()
                if team_name == DEFAULT_TEAM_NAME
            ),
            None,
        )

        state = {"year": today.year, "month": today.month}

        ui.label("Calendar").classes("text-4xl font-bold")

        team = ui.select(
            teams,
            value=default_team,
            label="Team",
            with_input=True,
            on_change=lambda: show_month.refresh(),
        ).classes("w-64")

        def go(step):
            state["year"], state["month"] = shift_month(
                state["year"], state["month"], step
            )
            show_month.refresh()

        def go_today():
            state["year"], state["month"] = (
                today.year,
                today.month,
            )
            show_month.refresh()

        def go_to(year, month):
            state["year"], state["month"] = year, month
            show_month.refresh()

        @ui.refreshable
        def show_month():
            year, month = state["year"], state["month"]
            games = {}
            latest = None
            if team.value is not None:
                with closing(
                    sqlite3.connect(DB_PATH)
                ) as conn:
                    games = team_games_in_month(
                        conn, team.value, year, month
                    )
                    if not games:
                        latest = latest_game_month(
                            conn, team.value, today
                        )

            with ui.row().classes("items-center"):
                ui.button(
                    icon="chevron_left",
                    on_click=lambda: go(-1),
                ).props("flat")
                ui.label(
                    f"{calendar.month_name[month]} {year}"
                ).classes("text-2xl w-48 text-center")
                ui.button(
                    icon="chevron_right",
                    on_click=lambda: go(1),
                ).props("flat")
                ui.button("Today", on_click=go_today).props(
                    "outline"
                )

            if not games:
                with ui.row().classes("items-center"):
                    ui.label(
                        "No games this month."
                    ).classes("text-gray-500")
                    if latest and latest != (year, month):
                        ui.button(
                            f"Go to most recent games "
                            f"({calendar.month_abbr[latest[1]]} {latest[0]})",
                            on_click=lambda: go_to(*latest),
                        ).props("flat")

            ui.html(
                build_calendar_html(
                    year, month, games, today
                )
            )

        show_month()

        ui.label(
            "Yellow dot = upcoming game. Grey = already played"
            " (with score). Gold = today."
        ).classes("text-sm")
