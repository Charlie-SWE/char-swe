from nicegui import ui


def section(title: str):
    ui.label(title).classes("font-mono-label gp-section")


# Builds the header with like "day ## month year at time"
def header(game: dict, info: dict | None, on_close):
    with ui.row().classes("w-full items-start justify-between no-wrap gap-2"):
        with ui.column().classes("gap-1 min-w-0"):

            # Shows the date of the game
            when = f"{game['date']:%a %d %b %Y}"

            # Shows the start time
            if info and info.get("start_time"):
                when += f" at {info['start_time']}"
            ui.label(when).classes("font-mono-label gp-eyebrow")

            # Shows either vs or at depending on who we are playing against
            prefix = ""
            if game.get("home"):
                prefix = "vs"
            else:
                prefix = "at"

            # Shows the opposing teams name
            ui.label(f"{prefix} {game['opponent']}").classes("font-display gp-title")

        # Has a close button in the header to close the panel
        ui.button(icon="close", on_click=on_close).props("flat round dense").classes(
            "gp-close"
        )


# Gets the game results
def result(game: dict, info: dict | None):
    # If the game has a score, show it!
    if game.get("score"):
        us, them = game["score"]

        # Calculates whether to show W L or D
        outcome = ""
        if us > them:
            outcome = "W"
        elif us < them:
            outcome = "L"
        else:
            outcome = "D"

        ui.label(f"{outcome} {us}-{them}").classes(
            f"font-display gp-score gp-{outcome.lower()}"
        )

    # If there is not any game infor available quit
    if not info:
        return


# Shows the location
def location(details: dict):
    section("LOCATION")
    place = details.get("place")

    # Says the place label in the ui row
    with ui.row().classes("items-center gap-2 no-wrap"):
        ui.label(place["label"]).classes("gp-strong")


# Formatter used for weather
def my_format(value, pattern: str):
    # If it doesn't exist just return a dash
    if value is None:
        return "-"

    # Otherwise! Format it
    return pattern.format(value)


# The weather section of the sidebar
def weather(details: dict):
    section("WEATHER")
    weather = details.get("weather")

    # Puts the weather icon and the label in a row
    with ui.row().classes("items-center gap-2 no-wrap"):
        ui.icon(weather["icon"]).classes("gp-icon gp-weather-icon")
        ui.label(weather["summary"]).classes("gp-strong")

    # The four columns of weather information
    weather_info = [
        [
            "High",
            my_format(weather.get("max_temp"), "{:.0f}°F"),
        ],
        [
            "Low",
            my_format(weather.get("min_temp"), "{:.0f}°F"),
        ],
        ["Rain", my_format(weather.get("precipitation"), "{:.2f} in")],
        [
            "Wind",
            my_format(weather.get("wind_speed"), "{:.0f} mph"),
        ],
    ]

    # Shows all of the information for the weather on the page
    with ui.element("div").classes("gp-tiles"):
        for i in range(len(weather_info)):
            # Then makes columns to show the weather information
            with ui.column().classes("gp-tile gap-0"):
                ui.label(weather_info[i][0]).classes("gp-tile-label")
                ui.label(weather_info[i][1]).classes("gp-tile-value")


# Shows the goals section
def goals(details: dict, game: dict):
    section("GOALS")

    # Tries to pull the goal
    goals = details.get("goals")

    info = details.get("info") or {}
    ours_name = info.get("our_name", "Kent St.")
    theirs_name = info.get("their_name", game["opponent"])

    # Iterates through all of the goals
    for goal in goals:

        # Makes a row for each goal
        with ui.row().classes(
            "gp-goal w-full no-wrap gap-3" + (" ours" if goal["ours"] else "")
        ):
            ui.label(goal["time"]).classes("gp-goal-time")

            # Shows info about the goal
            with ui.column().classes("gap-0 min-w-0 grow"):

                # Shows our name if the goal is ours
                if goal["ours"]:
                    ui.label(ours_name).classes("gp-goal-team")
                else:
                    ui.label(theirs_name).classes("gp-goal-team")

                # Shows who scored the goal
                ui.label(goal["scorer"]).classes("gp-goal-text")

                # Shows everyone who made an assist
                assists = goal["assists"]
                for name in assists:
                    ui.label(f"Assist: {name}").classes("gp-goal-assist")

            ui.label("-".join(str(s) for s in goal["score"])).classes("gp-goal-score")


# The team statistics section
def team_stats(details: dict, game: dict):
    stats = details.get("team_stats")

    # If we don't have any stats just return
    if not stats:
        return

    section("TEAM STATS")

    info = details.get("info") or {}
    ours_name = info.get("our_name", "Kent St.")
    theirs_name = info.get("their_name", game["opponent"])

    with ui.element("div").classes("gp-stats"):
        ui.label("")
        ui.label(ours_name).classes("gp-stats-head")
        ui.label(theirs_name).classes("gp-stats-head")

        # Shows the grid of all of the team stats
        for label, us, them in stats:
            ui.label(label).classes("gp-stats-label")
            ui.label(str(us)).classes("gp-stats-value")
            ui.label(str(them)).classes("gp-stats-value")


# Show player info
def show_player_info(player):
    name = f"{player['first_name']} {player['last_name']}"

    # Puts the players position next to their name
    if player.get("position"):
        name += f" ({player['position']})"

    # Shows the built name
    ui.label(name).classes("gp-players-name")

    for value in (
        round(player["minutes"] or 0),
        player["goals"],
        player["assists"],
        player["shots"],
    ):
        ui.label(str(value)).classes("gp-players-value")


# The player stats section
def players(details: dict):
    players = details.get("players") or []
    if not players:
        return
    section("KENT STATE PLAYERS")
    with ui.element("div").classes("gp-players"):

        # Builds out like the top bar of the grid
        for head in ("Player", "Min", "G", "A", "Sh"):
            ui.label(head).classes("gp-players-head")

        starters = []
        subs = []

        # Iterates through all players
        for p in players:
            if p["starter"]:
                starters.append(p)
            else:
                subs.append(p)

        # makes the starters section
        ui.label("Starters").classes("gp-players-group")
        for player in starters:
            show_player_info(player)

        # Makes the subs section
        ui.label("Subs").classes("gp-players-group")
        for player in subs:
            show_player_info(player)


# Shows the loadin panel
def render_loading(panel, game: dict, on_close):
    panel.clear()
    with panel:
        header(game, None, on_close)
        result(game, None)

        # Shows the NiceGUI spinner!
        with ui.row().classes("w-full justify-center py-10"):
            ui.spinner(size="32px").classes("gp-icon")


def render_details(panel, game: dict, details: dict, on_close):
    panel.clear()
    with panel:
        header(game, details.get("info"), on_close)
        result(game, details.get("info"))
        location(details)
        weather(details)
        goals(details, game)
        team_stats(details, game)
        players(details)
