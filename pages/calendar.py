import calendar
import sqlite3
from contextlib import closing
from datetime import date

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
from src.services.game_details import get_game_details

CSS = """
    .cal-grid  { display:grid; grid-template-columns:repeat(7, minmax(0, 1fr)); }
    .cal-head  { padding:10px 12px; font-family:'JetBrains Mono',monospace; font-size:11px; letter-spacing:.1em;
                 color:#7A849A; border-bottom:1px solid #E3E6EC; }
    .cal-cell  { min-height:104px; padding:8px; display:flex; flex-direction:column; gap:4px; min-width:0;
                 border-right:1px solid #EEF0F3; border-bottom:1px solid #EEF0F3; }
    .cal-cell:nth-child(7n) { border-right:0; }
    .cal-cell.outside { background:#FAFBFC; }
    .cal-cell.outside .cal-num { color:%(lightgray)s; }
    .cal-num   { width:26px; height:26px; border-radius:50%%; display:flex; align-items:center; justify-content:center;
                 font-size:13px; font-weight:600; color:#3D4860; }
    .cal-num.today { background:%(gold)s; color:%(dark2)s; font-weight:700; }
    .cal-cell.has-game { background:#EEF2F9; cursor:pointer; transition:background .15s; }
    .cal-cell.has-game:hover { background:#DCE5F3; }
    .cal-result { font-size:13px; font-weight:700; color:%(dark2)s; }
    .cal-opponent { font-size:12px; font-weight:600; line-height:1.3; color:%(dark)s; overflow-wrap:anywhere; }
    .cal-where { margin-top:auto; font-size:11px; line-height:1.3; color:#7A849A;
                 display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }

    /* Game side panel */
    .gp-eyebrow { color:#2C8ECD; }
    .gp-title { font-size:20px; font-weight:800; line-height:1.2; color:%(dark2)s; }
    .gp-close { color:#7A849A; }
    .gp-score { font-size:32px; font-weight:800; line-height:1; }
    .gp-score.gp-w { color:#1E7A46; }
    .gp-score.gp-l { color:#B42318; }
    .gp-score.gp-d { color:%(dark2)s; }
    .gp-section { margin-top:10px; padding-top:12px; border-top:1px solid #E3E6EC; width:100%%; color:#7A849A; }
    .gp-muted { font-size:13px; line-height:1.4; color:#55607A; }
    .gp-strong { font-size:14px; font-weight:600; color:%(dark2)s; }
    .gp-icon { color:%(dark)s; font-size:20px; }
    .gp-weather-icon { color:%(gold)s; font-size:24px; }
    .gp-tiles { display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:8px; width:100%%; }
    .gp-tile { background:#F4F6FA; border-radius:10px; padding:8px 10px; }
    .gp-tile-label { font-size:11px; color:#7A849A; }
    .gp-tile-value { font-size:15px; font-weight:700; color:%(dark2)s; }
    .gp-goal { padding:8px 10px; border-radius:10px; background:#F7F8FA; }
    .gp-goal.ours { background:#EEF2F9; }
    .gp-goal-time { font-family:'JetBrains Mono',monospace; font-size:12px; color:#7A849A; min-width:42px; padding-top:1px; }
    .gp-goal-team { font-size:12px; font-weight:700; color:%(dark2)s; }
    .gp-goal-text { font-size:13px; line-height:1.35; color:#3D4860; }
    .gp-goal-assist { font-size:12px; line-height:1.35; color:#7A849A; }
    .gp-goal-score { font-size:13px; font-weight:700; color:%(dark2)s; }
    .gp-stats { display:grid; grid-template-columns:1fr 80px 80px; row-gap:6px; width:100%%; }
    .gp-stats-head { font-size:12px; font-weight:700; color:%(dark2)s; text-align:right; }
    .gp-stats-label { font-size:13px; color:#55607A; }
    .gp-stats-value { font-size:13px; font-weight:600; color:%(dark2)s; text-align:right; }
    .gp-players { display:grid; grid-template-columns:1fr 40px 28px 28px 28px; row-gap:5px; width:100%%; }
    .gp-players-head { font-family:'JetBrains Mono',monospace; font-size:11px; color:#7A849A; text-align:right; }
    .gp-players-head:first-child { text-align:left; }
    .gp-players-group { grid-column:1 / -1; margin-top:6px; font-size:12px; font-weight:700; color:%(dark)s; }
    .gp-players-name { font-size:13px; color:#3D4860; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .gp-players-value { font-size:13px; font-weight:600; color:%(dark2)s; text-align:right; }
    .gp-players-value.zero { color:#B9C4D8; font-weight:400; }
""" % {
    "dark": PrimaryDarkHex,
    "dark2": SecondaryDarkHex,
    "gold": PrimaryLightHex,
    "lightgray": SecondaryLightGrayHex,
}

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


# Pulls in all of the game data
def get_games(year: int, month: int, db_path=DB_PATH) -> list[dict]:
    first = date(year, month, 1)
    nxt = date(year + month // 12, month % 12 + 1, 1)

    # Makes a new database connection
    with closing(sqlite3.connect(db_path)) as db:
        rows = db.execute(
            """
            SELECT g.game_date, g.home_team_id, g.home_score, g.away_score,
                   h.team_name, a.team_name, g.location,
                   g.game_id, g.away_team_id
            FROM Games g
            JOIN Teams h ON h.team_id = g.home_team_id
            JOIN Teams a ON a.team_id = g.away_team_id
            WHERE (g.home_team_id = ? OR g.away_team_id = ?)
              AND g.game_date >= ? AND g.game_date < ?
            ORDER BY g.game_date
            """,
            (
                OUR_TEAM_ID,
                OUR_TEAM_ID,
                first.isoformat(),
                nxt.isoformat(),
            ),
        ).fetchall()

    games = []

    # Iterates through every row and pulls the game data
    for (
        game_date,
        home_id,
        home_score,
        away_score,
        home_name,
        away_name,
        location,
        game_id,
        away_id,
    ) in rows:

        # Checks if we are the home team
        home = False
        if home_id == OUR_TEAM_ID:
            home = True

        # Make each game into a dictionary
        game = {
            "game_id": game_id,
            "date": date.fromisoformat(game_date),
            "home": home,
            "opponent": away_name if home else home_name,
            "opponent_id": away_id if home else home_id,
            "location": location,
            "score": (home_score, away_score),
        }

        games.append(game)
    return games


# The actual page stuff !!!
def init():
    @ui.page("/calendar")
    def calendar_page():
        frame("calendar")
        ui.add_css(CSS)

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
                "SCHEDULE",
                "Calendar",
                "Upcoming games, conditions and opponents.",
            )
            with ui.column().classes("card w-full gap-0 overflow-hidden"):
                month_view()
