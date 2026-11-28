import sqlite3
from contextlib import closing
from datetime import date

from langchain_core.tools import tool

from src.components.Scrape import DB_PATH
from src.services.game_details import (
    OUR_TEAM_ID,
    STATES,
    WEATHER_CODES,
    get_game_details,
    get_games,
)
from src.services.weather import get_weather

# Big enough to pull every game we have
ALL_GAMES = 1000

# Stats that can be ranked, and their column in PlayerGameStats
RANKABLE_STATS = {
    "goals": "s.goals",
    "assists": "s.assists",
    "points": "s.goals * 2 + s.assists",
    "shots": "s.shots",
    "shots_on_goal": "s.shots_on_goal",
    "minutes": "s.minutes_played",
    "starts": "s.starter",
    "saves": "s.saves",
    "yellow_cards": "s.yellow_cards",
    "red_cards": "s.red_cards",
    "fouls": "s.fouls",
}


# Turns a game from get_games into something easy for Rocky to read
def describe_game(g):
    our_score, their_score = g["score"]
    if not g["home"]:
        our_score = g["score"][1]
        their_score = g["score"][0]

    if our_score > their_score:
        result = "win"
    elif our_score < their_score:
        result = "loss"
    else:
        result = "draw"

    if g["home"]:
        venue = "home"
    else:
        venue = "away"

    return {
        "date": g["date"].isoformat(),
        "opponent": g["opponent"],
        "venue": venue,
        "our_score": our_score,
        "their_score": their_score,
        "result": result,
    }


def all_past_games():
    return get_games(games=ALL_GAMES)


@tool(
    description="Get Kent State's most recent games with the opponent, home or away, score and result."
)
def get_recent_games(count: int = 5):
    if count < 1:
        count = 1

    games = []
    for g in get_games(games=count):
        games.append(describe_game(g))
    return games


@tool(description="Get every Kent State game in a given month. month is 1 to 12.")
def get_games_in_month(year: int, month: int):
    if month < 1 or month > 12:
        return "month must be between 1 and 12"

    games = []
    for g in get_games(year=year, month=month):
        games.append(describe_game(g))
    return games


@tool(
    description="Get every game Kent State has played against an opponent, and the overall record against them. Part of the name is fine, like 'Akron'."
)
def get_games_against(opponent: str):
    search = opponent.strip().casefold()

    games = []
    record = {"wins": 0, "losses": 0, "draws": 0}
    for g in all_past_games():
        if g["opponent"] is None:
            continue
        if search not in g["opponent"].casefold():
            continue

        game = describe_game(g)
        games.append(game)
        if game["result"] == "win":
            record["wins"] += 1
        elif game["result"] == "loss":
            record["losses"] += 1
        else:
            record["draws"] += 1

    if not games:
        return f"No games found against {opponent}"

    return {"record": record, "games": games}


@tool(
    description="Get Kent State's win, loss and draw record and goals for and against in a season. season is the year, like 2025."
)
def get_season_record(season: int):
    record = {
        "season": season,
        "games": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "goals_for": 0,
        "goals_against": 0,
    }

    for g in all_past_games():
        if g["date"].year != season:
            continue

        game = describe_game(g)
        record["games"] += 1
        record["goals_for"] += game["our_score"]
        record["goals_against"] += game["their_score"]
        if game["result"] == "win":
            record["wins"] += 1
        elif game["result"] == "loss":
            record["losses"] += 1
        else:
            record["draws"] += 1

    if record["games"] == 0:
        return f"No games found in {season}"

    return record


@tool(
    description="Get the full details of one Kent State game: start time, who scored and assisted, team stats, weather and our players' stats. game_date is YYYY-MM-DD."
)
def get_game_info(game_date: str):
    try:
        day = date.fromisoformat(game_date)
    except ValueError:
        return "game_date must be in YYYY-MM-DD format"

    game = None
    for g in get_games(year=day.year, month=day.month):
        if g["date"] == day:
            game = g

    if game is None:
        return f"No game found on {game_date}"

    details = get_game_details(game)

    return {
        "game": describe_game(game),
        "place": details["place"],
        "info": details["info"],
        "goals": details["goals"],
        "team_stats": details["team_stats"],
        "weather": details["weather"],
        "players": details["players"],
    }


@tool(
    description="Get a Kent State player's total stats. Part of the name is fine. season is the year, or 0 for every season."
)
def get_player_stats(name: str, season: int = 0):
    sql = """
        SELECT p.first_name, p.last_name, p.position, p.jersey_number,
               COUNT(*) AS games,
               SUM(s.starter) AS starts,
               SUM(s.minutes_played) AS minutes,
               SUM(s.goals) AS goals,
               SUM(s.assists) AS assists,
               SUM(s.shots) AS shots,
               SUM(s.shots_on_goal) AS shots_on_goal,
               SUM(s.yellow_cards) AS yellow_cards,
               SUM(s.red_cards) AS red_cards,
               SUM(s.saves) AS saves,
               SUM(s.goals_against) AS goals_against
        FROM PlayerGameStats s
        JOIN Players p ON p.player_id = s.player_id
        JOIN Games g ON g.game_id = s.game_id
        WHERE s.team_id = ?
          AND s.participated = 1
          AND (p.first_name || ' ' || p.last_name) LIKE ?
    """
    params = [OUR_TEAM_ID, f"%{name.strip()}%"]

    if season != 0:
        sql += " AND strftime('%Y', g.game_date) = ?"
        params.append(str(season))

    sql += " GROUP BY p.player_id ORDER BY goals DESC"

    with closing(sqlite3.connect(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(sql, params).fetchall()

    players = []
    for row in rows:
        players.append(dict(row))

    if not players:
        return f"No Kent State player found matching {name}"

    return players


@tool(
    description="Get Kent State's top players for a stat. stat is one of: goals, assists, points, shots, shots_on_goal, minutes, starts, saves, yellow_cards, red_cards, fouls. season is the year, or 0 for every season."
)
def get_top_players(stat: str, count: int = 5, season: int = 0):
    if stat not in RANKABLE_STATS:
        return f"Unknown stat: {stat}. Use one of: {', '.join(RANKABLE_STATS)}"

    if count < 1:
        count = 1

    sql = f"""
        SELECT p.first_name, p.last_name, p.position,
               SUM({RANKABLE_STATS[stat]}) AS {stat},
               COUNT(*) AS games
        FROM PlayerGameStats s
        JOIN Players p ON p.player_id = s.player_id
        JOIN Games g ON g.game_id = s.game_id
        WHERE s.team_id = ?
          AND s.participated = 1
    """
    params = [OUR_TEAM_ID]

    if season != 0:
        sql += " AND strftime('%Y', g.game_date) = ?"
        params.append(str(season))

    sql += f" GROUP BY p.player_id ORDER BY {stat} DESC LIMIT ?"
    params.append(count)

    with closing(sqlite3.connect(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(sql, params).fetchall()

    players = []
    for row in rows:
        players.append(dict(row))
    return players


@tool(
    description="Get the Kent State roster with each player's position and jersey number. season is the year, or 0 for everyone who has played for us."
)
def get_roster(season: int = 0):
    sql = """
        SELECT p.first_name, p.last_name, p.position, p.jersey_number,
               COUNT(*) AS games
        FROM PlayerGameStats s
        JOIN Players p ON p.player_id = s.player_id
        JOIN Games g ON g.game_id = s.game_id
        WHERE s.team_id = ?
          AND s.participated = 1
    """
    params = [OUR_TEAM_ID]

    if season != 0:
        sql += " AND strftime('%Y', g.game_date) = ?"
        params.append(str(season))

    sql += " GROUP BY p.player_id ORDER BY p.last_name"

    with closing(sqlite3.connect(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(sql, params).fetchall()

    players = []
    for row in rows:
        players.append(dict(row))
    return players


@tool(
    description="Get the daily weather for a US city, in Fahrenheit, inches and mph. Works for past dates and up to 16 days ahead. Dates are YYYY-MM-DD. Leave end_date empty for one day."
)
def get_city_weather(city: str, state: str, start_date: str, end_date: str = ""):
    try:
        start_day = date.fromisoformat(start_date)
        end_day = start_day
        if end_date:
            end_day = date.fromisoformat(end_date)
    except ValueError:
        return "Dates must be in YYYY-MM-DD format"

    # The weather lookup needs the full state name
    state = STATES.get(state.strip().upper(), state)

    try:
        data = get_weather(city, state, start_day, end_day)
    except ValueError as e:
        return str(e)

    days = []
    for day in data["weather"]:
        summary, icon = WEATHER_CODES.get(day["weather_code"], ("Unknown", None))
        days.append(
            {
                "date": day["date"],
                "summary": summary,
                "min_temp": day["min_temp"],
                "max_temp": day["max_temp"],
                "precipitation": day["precipitation"],
                "wind_speed": day["wind_speed"],
            }
        )
    return days


# Every tool Rocky can use
TOOL_LIST = [
    get_recent_games,
    get_games_in_month,
    get_games_against,
    get_season_record,
    get_game_info,
    get_player_stats,
    get_top_players,
    get_roster,
    get_city_weather,
]
