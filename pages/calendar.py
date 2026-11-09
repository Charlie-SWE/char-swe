import calendar
import sqlite3

from nicegui import run, ui

from src.components.Scrape import DB_PATH
from src.components.Colors import (
    PrimaryDarkHex,
    PrimaryLightHex,
    SecondaryDarkHex,
    SecondaryLightGrayHex,
)
from pages.game_panel import render_details, render_loading
from src.components.Layout import (
    frame,
    page_body,
    page_header,
)
from src.services.game_details import get_game_details, get_games

# The ID of kent
OUR_TEAM_ID = 55287

# First day of the week is sunday
FIRST_WEEKDAY = calendar.SUNDAY


# Basically pulls the seven days of the week
def weekdays(first_weekday):
    weekdays = []
    for i in range(7):
        day = (first_weekday + i) % 7

        # Gets the days abbrevation
        cal_day = calendar.day_abbr[day]
        weekdays.append(cal_day.upper())

    return weekdays


WEEKDAYS = weekdays(FIRST_WEEKDAY)


# Builds the game result text
def result_text(game: dict) -> str:
    # akes the games score look nice
    if game.get("score"):
        us, them = game["score"]
        outcome = "W" if us > them else "L" if us < them else "D"
        return f"{outcome} {us}-{them}"

    # If the game doens't have a score just returns the games time
    return game.get("time") or ""


# Returns where the game is
def where_text(game: dict) -> str:
    # Returns the game location if it has one
    if game.get("location"):
        return game["location"]

    # Returns home if its a home game
    if game.get("home"):
        return "Home"

    # Returns nothing if it has neither :(
    return ""


# The actual page stuff !!!
def init():
    @ui.page("/calendar")
    def calendar_page():
        frame("calendar")

        # Gets todays date and month and year
        today = date.today()
        view = {"year": today.year, "month": today.month}

        # Dictionary of info about the selected game
        selected = {"game_id": None}

        # Makes the right drawer but hides it
        with (
            ui.right_drawer(value=False)
            .props("width=400 bordered")
            .classes("bg-white p-5") as drawer
        ):
            panel = ui.column().classes("w-full gap-3")

        # Closes the right drawer
        def close_panel():
            selected["game_id"] = None
            drawer.hide()

        # If this isn't async it breaks everything!!
        #
        async def open_game(game: dict):
            # Selects the current game
            selected["game_id"] = game["game_id"]

            # Shows the right drawer
            render_loading(panel, game, close_panel)
            drawer.show()

            # Uses the io_bound so that it doesn't freeze the app when I get the game details
            details = await run.io_bound(get_game_details, game)

            # Then shows the details
            render_details(panel, game, details, close_panel)

        # What happens when you press < or >
        def shift(delta: int):
            m = view["month"] - 1 + delta
            view["year"] += m // 12
            view["month"] = m % 12 + 1
            month_view.refresh()

        # The 'today' button
        def go_today():
            view.update(year=today.year, month=today.month)
            month_view.refresh()

        # The actual calendar part
        @ui.refreshable
        def month_view():
            y, m = view["year"], view["month"]
            games = get_games(y, m) or []
            by_day = {g["date"]: g for g in games}

            # Toolbar
            with (
                ui.row()
                .classes("w-full items-center justify-between no-wrap px-5 py-4")
                .style("border-bottom:1px solid #E3E6EC")
            ):
                # All of the stuff in the toolbar on the left
                with ui.row().classes("items-center gap-1 no-wrap"):

                    # Left Month
                    ui.button(
                        icon="chevron_left",
                        on_click=lambda d=-1: shift(d),
                    ).props("flat round dense").style(f"color:{PrimaryDarkHex}")

                    # Right Month
                    ui.button(
                        icon="chevron_right",
                        on_click=lambda d=1: shift(d),
                    ).props("flat round dense").style(f"color:{PrimaryDarkHex}")

                    # Shows the name of the month
                    ui.label(f"{calendar.month_name[m]} {y}").classes(
                        "font-display text-xl font-bold ml-2"
                    ).style(f"color:{SecondaryDarkHex}")

                # The today button
                ui.button("Today", on_click=go_today).props(
                    "outline no-caps dense"
                ).classes("px-3").style(
                    f"color:{PrimaryDarkHex}; border-radius:8px; font-weight:600"
                )

            # Grid
            with ui.element("div").classes("cal-grid w-full"):

                # Prints the weekdays in the top bar
                for wd in WEEKDAYS:
                    ui.label(wd).classes("cal-head")

                # Prints all of the days on the calendar
                for d in calendar.Calendar(FIRST_WEEKDAY).itermonthdates(y, m):
                    classes = "cal-cell"

                    # if the day is not in the month
                    if d.month != m:
                        classes += " outside"

                    # if there is a game on that day
                    g = by_day.get(d)
                    if g != None:
                        classes += " has-game"

                    # Makes a div
                    cell = ui.element("div").classes(classes)

                    # If the day has a game on it, you can click on it
                    if g:
                        cell.on(
                            "click",
                            lambda g=g: open_game(g),
                        )

                    # Inside the call
                    with cell:
                        cell_classes = "cal-num"

                        # If the cell is today, give it the today CSS
                        if d == today:
                            cell_classes += " today"

                        # Show the day as today
                        ui.label(str(d.day)).classes(cell_classes)

                        # If there is a game on the day
                        if g:
                            # Gets the result text
                            result = result_text(g)

                            # If there isn't any result text don't show it
                            if result:
                                result = result_text(g)
                                ui.label(result).classes("cal-result")

                            ui.label(g.get("opponent", "TBD")).classes("cal-opponent")

                            # Gets the location text
                            where = where_text(g)

                            # If there is location text, then show it
                            if where:
                                ui.label(where).classes("cal-where")

        with page_body():
            page_header(
                "Calendar",
                "Upcoming games, conditions and opponents.",
            )
            with ui.column().classes("card w-full gap-0 overflow-hidden"):
                month_view()
