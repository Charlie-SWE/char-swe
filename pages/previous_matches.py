import sqlite3
from contextlib import closing
from datetime import date

from nicegui import ui

from src.components.Layout import frame, page_body, page_header
from src.components.Scrape import DB_PATH

PAGE_SIZE = 50

LINEUP_COLUMNS = [
    {"name": "name", "label": "Player", "field": "name", "align": "left"},
    {"name": "position", "label": "Pos", "field": "position", "align": "left"},
    {"name": "minutes", "label": "Min", "field": "minutes"},
    {"name": "goals", "label": "G", "field": "goals"},
    {"name": "assists", "label": "A", "field": "assists"},
    {"name": "shots", "label": "Shots", "field": "shots"},
]


# Every game in the database, newest first
def load_games():
    with closing(sqlite3.connect(DB_PATH)) as db:
        rows = db.execute(
            """
            SELECT g.game_id, g.game_date,
                   g.home_team_id, h.team_name, g.home_score,
                   g.away_team_id, a.team_name, g.away_score
            FROM Games g
            JOIN Teams h ON h.team_id = g.home_team_id
            JOIN Teams a ON a.team_id = g.away_team_id
            ORDER BY g.game_date DESC, g.game_id DESC
            """
        ).fetchall()

    games = []
    for row in rows:
        games.append(
            {
                "game_id": row[0],
                "date": date.fromisoformat(row[1]),
                "home_id": row[2],
                "home": row[3],
                "home_score": row[4],
                "away_id": row[5],
                "away": row[6],
                "away_score": row[7],
            }
        )
    return games


# One team's players for one game
def get_lineup(game_id, team_id):
    with closing(sqlite3.connect(DB_PATH)) as db:
        return db.execute(
            """
            SELECT p.first_name, p.last_name, p.position,
                   s.starter, s.minutes_played, s.goals, s.assists, s.shots
            FROM PlayerGameStats s
            JOIN Players p ON p.player_id = s.player_id
            WHERE s.game_id = ? AND s.team_id = ? AND s.participated = 1
            ORDER BY s.starter DESC, s.goals DESC,
                     s.assists DESC, s.minutes_played DESC
            """,
            (game_id, team_id),
        ).fetchall()


# IDs of games where a player whose name contains the text played
def games_with_player(text):
    with closing(sqlite3.connect(DB_PATH)) as db:
        rows = db.execute(
            """
            SELECT DISTINCT s.game_id
            FROM PlayerGameStats s
            JOIN Players p ON p.player_id = s.player_id
            WHERE p.first_name || ' ' || p.last_name LIKE ?
            """,
            (f"%{text}%",),
        ).fetchall()
    return {row[0] for row in rows}


# All the text a game can be found by: teams, dates, and score
def search_text(game):
    d = game["date"]
    parts = [
        game["home"],
        game["away"],
        f"{d:%b %d %Y}",
        f"{d:%B}",
        d.isoformat(),
        f"{d.month}/{d.day}/{d.year}",
    ]
    if has_score(game):
        parts.append(f"{game['home_score']}-{game['away_score']}")
    return " ".join(parts).lower()


def has_score(game):
    return game["home_score"] is not None and game["away_score"] is not None


# W, L, D from one team's point of view, or "-" if there's no score
def outcome(game, team_id):
    if not has_score(game):
        return "-"
    if game["home_id"] == team_id:
        us, them = game["home_score"], game["away_score"]
    else:
        us, them = game["away_score"], game["home_score"]
    if us > them:
        return "W"
    if us < them:
        return "L"
    return "D"


# Fills a container with both teams' starters and subs
def show_lineups(game, container):
    container.clear()
    with container:
        for team_name, team_id in (
            (game["home"], game["home_id"]),
            (game["away"], game["away_id"]),
        ):
            ui.label(team_name).classes("font-display text-lg font-bold pt-2")
            players = get_lineup(game["game_id"], team_id)

            if not players:
                ui.label("No lineup data.").style("color:#7A849A")
                continue

            for title, is_starter in (("STARTERS", 1), ("SUBSTITUTES", 0)):
                group = [p for p in players if p[3] == is_starter]
                if not group:
                    continue

                ui.label(title).classes("font-mono-label pt-1")
                rows = [
                    {
                        "name": f"{p[0]} {p[1]}",
                        "position": p[2] or "-",
                        "minutes": round(p[4] or 0),
                        "goals": p[5],
                        "assists": p[6],
                        "shots": p[7],
                    }
                    for p in group
                ]
                ui.table(columns=LINEUP_COLUMNS, rows=rows).props(
                    "flat dense"
                ).classes("w-full")


def init():
    @ui.page("/previous_matches")
    def previous_matches_page():
        frame("history")

        games = load_games()
        for g in games:
            g["search"] = search_text(g)
        teams = {}
        for g in games:
            teams[g["home_id"]] = g["home"]
            teams[g["away_id"]] = g["away"]
        teams = dict(sorted(teams.items(), key=lambda t: t[1]))
        years = sorted({g["date"].year for g in games}, reverse=True)

        state = {"limit": PAGE_SIZE, "player_games": set()}

        with page_body():
            page_header("Match History", "Every match in the database and who played.")

            # Filters
            with ui.column().classes("card w-full p-4 gap-3"):
                # Row 1: dropdown filters (team boxes stretch, the rest stay small)
                with ui.row().classes("w-full gap-3 items-center no-wrap"):
                    team = (
                        ui.select(teams, label="Team", with_input=True, clearable=True)
                        .props("outlined dense")
                        .classes("flex-1 min-w-0")
                    )
                    opponent = (
                        ui.select(
                            teams, label="Opponent", with_input=True, clearable=True
                        )
                        .props("outlined dense")
                        .classes("flex-1 min-w-0")
                    )
                    venue = (
                        ui.select(["Home", "Away"], label="Home?", clearable=True)
                        .props("outlined dense")
                        .classes("w-28")
                        .bind_enabled_from(team, "value")
                    )
                    result = (
                        ui.select(["W", "L", "D"], label="Win?", clearable=True)
                        .props("outlined dense")
                        .classes("w-24")
                        .bind_enabled_from(team, "value")
                    )
                    year = (
                        ui.select(years, label="Season", clearable=True)
                        .props("outlined dense")
                        .classes("w-28")
                    )

                # Row 2: search
                search = (
                    ui.input("Search")
                    .props("outlined dense clearable debounce=300")
                    .classes("w-full")
                )
                with search.add_slot("prepend"):
                    ui.icon("search")

            def matches(g):
                text = (search.value or "").strip().lower()
                if text:
                    # Every word must appear in the game's text, or a player matched
                    words_match = all(w in g["search"] for w in text.split())
                    if not words_match and g["game_id"] not in state["player_games"]:
                        return False

                sides = (g["home_id"], g["away_id"])
                if team.value and team.value not in sides:
                    return False
                if opponent.value and opponent.value not in sides:
                    return False
                if team.value and venue.value:
                    is_home = g["home_id"] == team.value
                    if is_home != (venue.value == "Home"):
                        return False
                if team.value and result.value:
                    if outcome(g, team.value) != result.value:
                        return False
                if year.value and g["date"].year != year.value:
                    return False
                return True

            # Match list, rebuilt whenever a filter changes
            @ui.refreshable
            def game_list():
                shown = [g for g in games if matches(g)]

                ui.label(
                    f"{len(shown):,} match{'es' if len(shown) != 1 else ''}"
                ).style("color:#55607A")

                if not shown:
                    ui.label("No matches found for these filters.").style(
                        "color:#7A849A"
                    )
                    return

                for g in shown[: state["limit"]]:
                    score = (
                        f"{g['home_score']}-{g['away_score']}"
                        if has_score(g)
                        else "vs"
                    )
                    title = f"{g['date']:%b %d, %Y}  ·  {g['home']} {score} {g['away']}"
                    if team.value:
                        title = f"{outcome(g, team.value)}  ·  {title}"

                    with ui.expansion(title).classes("card w-full") as row:
                        box = ui.column().classes("w-full")

                    # Load lineups only when the row is opened
                    row.on_value_change(
                        lambda e, g=g, box=box: e.value and show_lineups(g, box)
                    )

                remaining = len(shown) - state["limit"]
                if remaining > 0:
                    ui.button(
                        f"Show more ({remaining:,} left)",
                        icon="expand_more",
                        on_click=show_more,
                    ).props("flat no-caps").classes("self-center")

            def show_more():
                state["limit"] += PAGE_SIZE
                game_list.refresh()

            def on_filter_change():
                state["limit"] = PAGE_SIZE
                game_list.refresh()

            def on_search_change():
                text = (search.value or "").strip()
                # Only look up players once there's enough to search for
                state["player_games"] = games_with_player(text) if len(text) >= 2 else set()
                on_filter_change()

            game_list()

            search.on_value_change(on_search_change)
            for f in (team, opponent, venue, result, year):
                f.on_value_change(on_filter_change)
