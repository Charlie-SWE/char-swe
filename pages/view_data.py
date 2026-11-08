import sqlite3
from contextlib import closing

from nicegui import run, ui

from src.components.Layout import frame, page_body, page_header
from src.components.Scrape import is_complete
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


def pretty(col: str) -> str:
    return col.replace("_", " ").title()


def fetch_rows(sql: str, params: list) -> list[dict]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return run_query(conn, sql, params)


def init():
    @ui.page("/view-data")
    def view_data_page():
        frame("data")

        with closing(sqlite3.connect(DB_PATH)) as conn:
            teams = list_teams(conn)
            downloading = not is_complete(conn)
        default_team = next(
            (
                team_id
                for team_id, team_name in teams.items()
                if team_name == DEFAULT_TEAM_NAME
            ),
            None,
        )
        column_options = {col: pretty(col) for col in COLUMNS}

        with page_body():
            page_header(
                "HISTORY", "View Data", "Historical results and player statistics."
            )

            if downloading:
                with ui.row().classes("vd-notice w-full items-center no-wrap"):
                    ui.spinner(size="18px").classes("vd-notice-spinner")
                    ui.label(
                        "Game data is still downloading in the background. "
                        "Results may be incomplete."
                    ).classes("vd-notice-text")

            # Filters
            with ui.column().classes("card vd-filters w-full"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label("Filters").classes("vd-title")
                    ui.button(
                        "Reset", icon="restart_alt", on_click=lambda: reset()
                    ).props("flat no-caps dense")

                with ui.element("div").classes("vd-filter-grid w-full"):
                    name = ui.input("Player name contains").props(
                        "outlined dense clearable"
                    )
                    team = (
                        ui.select(
                            teams,
                            value=default_team,
                            label="Team",
                            clearable=True,
                            with_input=True,
                        )
                        .props("outlined dense")
                        .classes("team-select")
                    )
                    position = ui.select(
                        list(POSITION_GROUPS), label="Position", clearable=True
                    ).props("outlined dense")
                    order_by = ui.select(
                        column_options, label="Order by", value="last_name"
                    ).props("outlined dense")

                with ui.row().classes("vd-columns-row w-full items-end no-wrap"):
                    columns = (
                        ui.select(
                            column_options,
                            label="Columns",
                            multiple=True,
                            value=[c for c in COLUMNS if c in DEFAULT_COLUMNS],
                        )
                        .props("outlined dense use-chips")
                        .classes("flex-grow")
                    )
                    show_button = (
                        ui.button("Show data", icon="search", color=None)
                        .props("unelevated no-caps")
                        .classes("vd-show-button")
                    )

            # Results
            with ui.column().classes("card vd-results w-full"):
                with ui.row().classes("vd-results-head w-full items-center"):
                    ui.label("Players").classes("vd-title")
                    count = ui.label("").classes("vd-count")
                    count.set_visibility(False)
                results = ui.column().classes("vd-rows w-full")

        def empty_state(icon: str, text: str):
            with results:
                with ui.column().classes("vd-empty w-full items-center justify-center"):
                    ui.icon(icon).classes("vd-empty-icon")
                    ui.label(text).classes("vd-empty-text")

        def reset():
            name.value = ""
            team.value = default_team
            position.value = None
            order_by.value = "last_name"
            columns.value = [c for c in COLUMNS if c in DEFAULT_COLUMNS]

        async def show_data():
            selected = [c for c in COLUMNS if c in (columns.value or [])]
            if not selected:
                ui.notify("Select at least one column.", type="warning")
                return

            results.clear()
            count.set_visibility(False)
            show_button.props("loading")
            try:
                filters = PlayerFilters(
                    columns=selected,
                    name=name.value,
                    team_id=team.value,
                    position=position.value,
                    order_by=order_by.value,
                )
                sql, params = build_player_query(filters)
                rows = await run.io_bound(fetch_rows, sql, params)
            except Exception as e:
                ui.notify(str(e), type="negative")
                empty_state("error_outline", "Couldn't load data.")
                return
            finally:
                show_button.props(remove="loading")

            if not rows:
                empty_state(
                    "search_off", "No matching players found in the scraped game data."
                )
                return

            count.text = f"{len(rows)} row{'s' if len(rows) != 1 else ''}"
            count.set_visibility(True)
            with results:
                ui.table(
                    columns=[
                        {
                            "name": c,
                            "label": pretty(c),
                            "field": c,
                            "sortable": True,
                            "align": "left",
                        }
                        for c in filters.columns
                    ],
                    rows=rows,
                    pagination=25,
                ).props("flat").classes("data-table w-full")

        show_button.on_click(show_data)
        name.on("keydown.enter", show_data)
        empty_state("table_chart", "Set your filters and click Show data.")
