import sqlite3
from contextlib import closing

from nicegui import run, ui
from src.components.Layout import frame
from src.components.Scrape import downloading
from src.services.query_builder import (
    COLUMNS,
    DB_PATH,
    POSITION_GROUPS,
    PlayerFilters,
    build_player_query,
    list_teams,
    run_query,
)

DEFAULT_COLUMNS = PlayerFilters().columns
DEFAULT_TEAM_NAME = "Kent State University"


def fetch_rows(sql: str, params: list) -> list[dict]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return run_query(conn, sql, params)


def init():
    @ui.page('/view-data')
    def view_data_page():
        frame()
        ui.label('View Player Data').classes('text-4xl font-bold')

        with closing(sqlite3.connect(DB_PATH)) as conn:
            teams = list_teams(conn)
        if downloading.is_set():
            ui.label(
                "Game data is still downloading in the"
                " background. Results may be incomplete."
            ).classes("text-orange-600")
        default_team = next(
            (
                team_id
                for team_id, team_name in teams.items()
                if team_name == DEFAULT_TEAM_NAME
            ),
            None,
        )

        ui.label("Columns").classes("text-lg")
        with ui.row():
            checkboxes = {
                col: ui.checkbox(
                    col, value=col in DEFAULT_COLUMNS
                )
                for col in COLUMNS
            }

        with ui.row().classes("items-end"):
            name = ui.input("Player name contains")
            team = ui.select(
                teams,
                value=default_team,
                label="Team",
                clearable=True,
                with_input=True,
            ).classes("w-64")
            position = ui.select(
                list(POSITION_GROUPS),
                label="Position",
                clearable=True,
            ).classes("w-32")
            order_by = ui.select(
                list(COLUMNS),
                label="Order by",
                value="last_name",
            ).classes("w-40")

        show_button = ui.button("Show Data")

        results = ui.column().classes("w-full")

        async def show_data():
            results.clear()
            try:
                filters = PlayerFilters(
                    columns=[
                        col
                        for col, box in checkboxes.items()
                        if box.value
                    ],
                    name=name.value,
                    team_id=team.value,
                    position=position.value,
                    order_by=order_by.value,
                )
                sql, params = build_player_query(filters)
                rows = await run.io_bound(
                    fetch_rows, sql, params
                )
            except Exception as e:
                ui.notify(str(e), type="negative")
                return

            with results:
                if not rows:
                    ui.label(
                        "No matching players found in the"
                        " scraped game data."
                    ).classes("text-gray-500")
                    return
                ui.label(f"{len(rows)} row(s)")
                ui.table(
                    columns=[
                        {
                            "name": col,
                            "label": col,
                            "field": col,
                            "sortable": True,
                        }
                        for col in filters.columns
                    ],
                    rows=rows,
                    pagination=25,
                ).classes("w-full")

        show_button.on_click(show_data)

        