import sqlite3
import time
from contextlib import closing
from datetime import date

from src.components.Scrape import DB_PATH, get_api_data
from src.services.weather import get_weather

OUR_TEAM_ID = 55287

HOME_CITY = "Kent"
HOME_STATE = "Ohio"

# All of the two letter state codes, and DC
STATES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}

# All of the weather codes and their icon
WEATHER_CODES = {
    0: ("Clear", "wb_sunny"),
    1: ("Mostly clear", "wb_sunny"),
    2: ("Partly cloudy", "partly_cloudy_day"),
    3: ("Overcast", "cloud"),
    45: ("Fog", "foggy"),
    48: ("Freezing fog", "foggy"),
    51: ("Light drizzle", "grain"),
    53: ("Drizzle", "grain"),
    55: ("Heavy drizzle", "grain"),
    56: ("Freezing drizzle", "grain"),
    57: ("Freezing drizzle", "grain"),
    61: ("Light rain", "water_drop"),
    63: ("Rain", "water_drop"),
    65: ("Heavy rain", "water_drop"),
    66: ("Freezing rain", "water_drop"),
    67: ("Freezing rain", "water_drop"),
    71: ("Light snow", "ac_unit"),
    73: ("Snow", "ac_unit"),
    75: ("Heavy snow", "ac_unit"),
    77: ("Snow grains", "ac_unit"),
    80: ("Light showers", "umbrella"),
    81: ("Showers", "umbrella"),
    82: ("Heavy showers", "umbrella"),
    85: ("Snow showers", "ac_unit"),
    86: ("Heavy snow showers", "ac_unit"),
    95: ("Thunderstorm", "thunderstorm"),
    96: ("Thunderstorm with hail", "thunderstorm"),
    99: ("Thunderstorm with hail", "thunderstorm"),
}

# All of the different team statistics
TEAM_STATS = [
    ("Shots", None, "shots"),
    ("Shots on goal", None, "shotsOnGoal"),
    ("Corners", None, "corners"),
    ("Offsides", None, "offsides"),
    ("Fouls", "penalties", "fouls"),
    ("Yellow cards", "penalties", "yellowCards"),
    ("Red cards", "penalties", "redCards"),
    ("Saves", "goalie", "saves"),
]

cache = {}


# Gets list of teams
def get_teams():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT team_name FROM Teams ORDER BY team_name").fetchall()
    conn.close()

    teams = []
    for row in rows:
        teams.append(row[0])
    return teams


# Gets the venue of the team
def get_home_venue(team_id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        """
        SELECT location FROM Games
        WHERE home_team_id = ? AND location IS NOT NULL
        GROUP BY location
        ORDER BY COUNT(*) DESC
        LIMIT 1
        """,
        (team_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return None
    return row[0]


# Gets all of the players in the game
def get_our_players(game_id):
    # Pulls data from the database
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """
        SELECT p.first_name, p.last_name, p.position,
               s.starter, s.minutes_played, s.goals,
               s.assists, s.shots
        FROM PlayerGameStats s
        JOIN Players p ON p.player_id = s.player_id
        WHERE s.game_id = ? AND s.team_id = ?
          AND s.participated = 1
        ORDER BY s.starter DESC, s.goals DESC,
                 s.assists DESC, s.minutes_played DESC
        """,
        (game_id, OUR_TEAM_ID),
    ).fetchall()
    conn.close()

    # Puts all of the data in a list
    players = []
    for row in rows:
        players.append(
            {
                "first_name": row[0],
                "last_name": row[1],
                "position": row[2],
                "starter": row[3],
                "minutes": row[4],
                "goals": row[5],
                "assists": row[6],
                "shots": row[7],
            }
        )

    # Returns the list
    return players


# Runs get_api_data
def short_sleep(seconds):
    time.sleep(min(seconds, 1))


# Runs get_api_data
def fetch(path):
    return get_api_data(path, sleep=short_sleep)


# Pulls the location from the location text
def parse_location(text):
    parts = []
    for part in text.split(","):
        if part.strip():
            parts.append(part.strip())

    if len(parts) < 2:
        return None

    city = parts[-2]
    state = parts[-1]
    state = STATES.get(state.upper(), state)
    return {"label": text, "city": city, "state": state}


def find_place(game):
    # Gets the game location
    if game.get("location"):
        place = parse_location(game["location"])
        if place:
            return place

    # If the game is home, it prints that
    if game.get("home"):
        return {
            "label": f"{HOME_CITY}, {HOME_STATE}",
            "city": HOME_CITY,
            "state": HOME_STATE,
        }

    # If its not a home game it has to pull the venue
    venue = get_home_venue(game["opponent_id"])
    if venue:
        return parse_location(venue)
    return None


# Gets the weather from the game
def get_game_weather(place, day):
    data = get_weather(place["city"], place["state"], day)
    weather = data["weather"][0]

    # Uses the weather code to get the icon and text
    summary, icon = WEATHER_CODES.get(
        weather["weather_code"], ("Unknown", "help_outline")
    )
    weather["summary"] = summary
    weather["icon"] = icon
    return weather


# Gets the start time of the game
def get_start_time(contest):
    if not contest.get("hasStartTime") or not contest.get("startTime"):
        return None

    hour, minute = contest["startTime"].split(":")
    hour = int(hour)
    minute = int(minute)

    # Sets to either AM or PM
    am_pm = "AM"
    if hour >= 12:
        am_pm = "PM"

    # Gets the hour the game occured
    hour = hour % 12
    if hour == 0:
        hour = 12

    return f"{hour}:{minute:02d} {am_pm}"


# Gets the information about the game
def get_info(game_id):
    data = fetch(f"/game/{game_id}")
    contest = data["contests"][0]

    our_name = "Kent St."
    their_name = "Opponent"
    for team in contest["teams"]:
        if str(team["teamId"]) == str(OUR_TEAM_ID):
            our_name = team.get("nameShort", our_name)
        else:
            their_name = team.get("nameShort", their_name)

    return {
        "start_time": get_start_time(contest),
        "our_name": our_name,
        "their_name": their_name,
    }


# Splits up the goal text to get who actually scored and actually assisted
def split_goal_text(text):
    if " (Assist by " not in text:
        return text.split(" (")[0].strip(), []

    scorer, assist_text = text.split(" (Assist by ", 1)
    assist_text = assist_text.rstrip(")").replace(" and ", ", ")

    assists = []
    for name in assist_text.split(","):
        if name.strip():
            assists.append(name.strip())
    return scorer.strip(), assists


# Gets all of the goals that were scored
def get_goals(game_id, home):
    summary = fetch(f"/game/{game_id}/scoring-summary")

    goals = []

    # Iterates through all of the periods of the game
    for period in summary.get("periods") or []:

        # Iterates through the game summary
        for item in period.get("summary") or []:
            if home:
                score = (item.get("homeScore"), item.get("visitScore"))
            else:
                score = (item.get("visitScore"), item.get("homeScore"))

            scorer, assists = split_goal_text(item.get("scoreText", ""))

            # Adds each goal to the list of goals
            goals.append(
                {
                    "time": item.get("time", ""),
                    "ours": str(item.get("teamId")) == str(OUR_TEAM_ID),
                    "scorer": scorer,
                    "assists": assists,
                    "score": score,
                }
            )
    return goals


def get_stat(stats, group, key):
    if group:
        stats = stats.get(group) or {}
    return stats.get(key) or "0"


# Gets all of the team stats
def get_team_stats(game_id):
    box = fetch(f"/game/{game_id}/team-stats")

    ours = {}
    theirs = {}

    # Iterates through the states and decides if it is ours or not
    for team in box.get("teamBoxscore") or []:
        if str(team.get("teamId")) == str(OUR_TEAM_ID):
            ours = team.get("teamStats") or {}
        else:
            theirs = team.get("teamStats") or {}

    stats = []
    for label, group, key in TEAM_STATS:
        stats.append((label, get_stat(ours, group, key), get_stat(theirs, group, key)))
    return stats


# Pulls all of the game details
def get_game_details(game):
    # Sets the game ID
    game_id = game["game_id"]

    # If the game data is already cached, just return it
    if game_id in cache:
        return cache[game_id]

    home = game.get("home", False)
    place = find_place(game)

    # Builds all of the game details
    details = {
        "place": place,
        "info": None,
        "goals": None,
        "team_stats": None,
        "weather": None,
        "players": [],
    }
    failed = False

    # Uses all of the helper functions to pull all of the game info
    try:
        details["info"] = get_info(game_id)
    except Exception:
        failed = True

    try:
        details["goals"] = get_goals(game_id, home)
    except Exception:
        failed = True

    try:
        details["team_stats"] = get_team_stats(game_id)
    except Exception:
        failed = True

    if place:
        try:
            details["weather"] = get_game_weather(place, game["date"])
        except Exception:
            failed = True

    try:
        details["players"] = get_our_players(game_id)
    except Exception:
        failed = True

    # It does all of the in their own try because we can still how game data even if its not 100% good
    # I just don't want to cache it
    if not failed:
        cache[game_id] = details

    # Returns all of the game info
    return details


# Pulls in all of the game data
def get_games(
    year: int | None = None,  # The year the games are in
    month: int | None = None,  # The month the games are in
    db_path=DB_PATH,
    games: int = -1,  # Pulls X recent games
) -> list[dict]:

    # Makes a new database connection
    with closing(sqlite3.connect(db_path)) as db:
        if games == -1:

            # Only pulls these if the user does pass games count
            first = date(year, month, 1)
            nxt = date(year + month // 12, month % 12 + 1, 1)

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
        else:
            # If we pass in games as something that isn't -1
            # Then we don't care about month or year anymore :)

            rows = db.execute(
                """
                SELECT g.game_date, g.home_team_id, g.home_score, g.away_score,
                       h.team_name, a.team_name, g.location,
                       g.game_id, g.away_team_id
                FROM Games g
                JOIN Teams h ON h.team_id = g.home_team_id
                JOIN Teams a ON a.team_id = g.away_team_id
                WHERE (g.home_team_id = ? OR g.away_team_id = ?)
                  AND g.game_date <= ?
                ORDER BY g.game_date DESC
                LIMIT ?
                """,
                (
                    OUR_TEAM_ID,
                    OUR_TEAM_ID,
                    date.today().isoformat(),
                    games,
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
