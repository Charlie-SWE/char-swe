import sqlite3
from contextlib import closing

from nicegui import run, ui

from src.components.Colors import PrimaryDarkHex, PrimaryLightHex, SecondaryDarkHex
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

CSS = """
.data-table thead th { font-family:'JetBrains Mono',monospace; font-size:11px; letter-spacing:.08em;
                       text-transform:uppercase; color:#7A849A; background:#F7F8FA; }
.data-table tbody td { font-size:14px; color:#2A3550; }
.data-table tbody tr:hover td { background:#F4F6FA; }
.filter-label { font-family:'JetBrains Mono',monospace; font-size:11px; letter-spacing:.1em; color:#7A849A; }
"""


def pretty(col: str) -> str:
    return col.replace("_", " ").title()


def fetch_rows(sql: str, params: list) -> list[dict]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return run_query(conn, sql, params)


def init():
    @ui.page("/view-data")
    def view_data_page():
        frame("data")
        ui.add_css(CSS)

        with closing(sqlite3.connect(DB_PATH)) as conn:
            teams = list_teams(conn)
            downloading = not is_complete(conn)
        default_team = next(
            (team_id for team_id, team_name in teams.items() if team_name == DEFAULT_TEAM_NAME),
            None,
        )
        column_options = {col: pretty(col) for col in COLUMNS}

        with page_body():
            page_header("HISTORY", "View Data", "Historical results and player statistics.")

            if downloading:
                with ui.row().classes("w-full items-center gap-3 no-wrap rounded-xl px-4 py-3").style(
                    "background:#FFF7E0; border:1px solid #F5D98A; color:#6B4E00"
                ):
                    ui.spinner(size="18px").style("color:#B07A00")
                    ui.label(
                        "Game data is still downloading in the background. Results may be incomplete."
                    ).classes("text-sm font-medium")

            # Filters
            with ui.column().classes("card w-full p-5 gap-4"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label("Filters").classes("font-display text-lg font-bold").style(
                        f"color:{SecondaryDarkHex}"
                    )
                    ui.button("Reset", icon="restart_alt", on_click=lambda: reset()).props(
                        "flat no-caps dense"
                    ).style("color:#55607A")

                with ui.element("div").classes("w-full grid gap-3").style(
                    "grid-template-columns:repeat(auto-fit,minmax(200px,1fr))"
                ):
                    name = ui.input("Player name contains").props("outlined dense clearable")
                    team = ui.select(
                        teams, value=default_team, label="Team", clearable=True, with_input=True
                    ).props("outlined dense").classes("team-select")
                    position = ui.select(
                        list(POSITION_GROUPS), label="Position", clearable=True
                    ).props("outlined dense")
                    order_by = ui.select(column_options, label="Order by", value="last_name").props(
                        "outlined dense"
                    )

                with ui.row().classes("w-full items-end gap-3 no-wrap"):
                    columns = ui.select(
                        column_options,
                        label="Columns",
                        multiple=True,
                        value=[c for c in COLUMNS if c in DEFAULT_COLUMNS],
                    ).props("outlined dense use-chips").classes("flex-grow")
                    show_button = ui.button("Show data", icon="search").props("unelevated no-caps").style(
                        f"background:{PrimaryLightHex} !important; color:{SecondaryDarkHex};"
                        "font-weight:700; border-radius:10px; height:40px"
                    )

            # Results
            with ui.column().classes("card w-full p-0 gap-0 overflow-hidden"):
                with ui.row().classes("w-full items-center gap-2 px-5 py-4").style(
                    "border-bottom:1px solid #E3E6EC"
                ):
                    ui.label("Players").classes("font-display text-lg font-bold").style(
                        f"color:{SecondaryDarkHex}"
                    )
                    count = ui.label("").classes("text-xs font-semibold px-2 py-0.5 rounded-full").style(
                        f"background:#EEF2F9; color:{PrimaryDarkHex}"
                    )
                    count.set_visibility(False)
                results = ui.column().classes("w-full gap-0")

        def empty_state(icon: str, text: str):
            with results:
                with ui.column().classes("w-full items-center justify-center gap-2 py-16"):
                    ui.icon(icon).style("color:#B9C4D8; font-size:36px")
                    ui.label(text).classes("text-sm").style("color:#7A849A")

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
                empty_state("search_off", "No matching players found in the scraped game data.")
                return

            count.text = f"{len(rows)} row{'s' if len(rows) != 1 else ''}"
            count.set_visibility(True)
            with results:
                ui.table(
                    columns=[
                        {"name": c, "label": pretty(c), "field": c, "sortable": True, "align": "left"}
                        for c in filters.columns
                    ],
                    rows=rows,
                    pagination=25,
                ).props("flat").classes("data-table w-full")

        show_button.on_click(show_data)
        name.on("keydown.enter", show_data)
        empty_state("table_chart", "Set your filters and click Show data.")
