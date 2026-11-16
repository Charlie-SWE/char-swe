import sqlite3
from datetime import date

import src.services.game_details as gd


# Test location with a state abbreviation
def test_parse_location():
    result = gd.parse_location("Kent, OH")
    assert result["city"] == "Kent"
    assert result["state"] == "Ohio"


# Test location with a full state name
def test_parse_location_full_state():
    result = gd.parse_location("Akron, Ohio")
    assert result["city"] == "Akron"
    assert result["state"] == "Ohio"


# Test a wrong location
def test_invalid_location():
    assert gd.parse_location("Kent") is None


# Test a home game location
def test_home_location():
    game = {"home": True}
    result = gd.find_place(game)
    assert result["city"] == "Kent"
    assert result["state"] == "Ohio"


# Test an away game location
def test_away_location(monkeypatch):
    monkeypatch.setattr(
        gd, "get_home_venue",
        lambda team_id: "Akron, OH"
    )

    game = {"home": False, "opponent_id": 10}
    result = gd.find_place(game)
    assert result["city"] == "Akron"


# Test an unknown away location
def test_missing_location(monkeypatch):
    monkeypatch.setattr(gd, "get_home_venue", lambda team_id: None)

    game = {"home": False, "opponent_id": 10}
    assert gd.find_place(game) is None


# Test morning game time
def test_morning_time():
    contest = {"hasStartTime": True, "startTime": "09:30"}
    assert gd.get_start_time(contest) == "9:30 AM"


# Test afternoon game time
def test_afternoon_time():
    contest = {"hasStartTime": True, "startTime": "15:45"}
    assert gd.get_start_time(contest) == "3:45 PM"


# Test midnight and noon
def test_special_times():
    assert gd.get_start_time(
        {"hasStartTime": True, "startTime": "00:00"}
    ) == "12:00 AM"

    assert gd.get_start_time(
        {"hasStartTime": True, "startTime": "12:00"}
    ) == "12:00 PM"


# Test a game without a start time
def test_missing_time():
    assert gd.get_start_time({}) is None


# Test a goal without an assist
def test_goal_without_assist():
    scorer, assists = gd.split_goal_text("John Smith (Goal)")
    assert scorer == "John Smith"
    assert assists == []


# Test a goal with multiple assists
def test_goal_with_assists():
    scorer, assists = gd.split_goal_text(
        "John Smith (Assist by Bob Jones and Mike Lee)"
    )
    assert scorer == "John Smith"
    assert assists == ["Bob Jones", "Mike Lee"]


# Test normal statistics
def test_get_stat():
    stats = {"shots": 8}
    assert gd.get_stat(stats, None, "shots") == 8


# Test missing statistics
def test_missing_stat():
    assert gd.get_stat({}, None, "shots") == "0"
    assert gd.get_stat({}, "penalties", "fouls") == "0"


# Test nested statistics
def test_nested_stat():
    stats = {"penalties": {"fouls": 4}}
    assert gd.get_stat(stats, "penalties", "fouls") == 4


# Test weather information
def test_game_weather(monkeypatch):
    def fake_weather(city, state, day):
        return {"weather": [{"weather_code": 0}]}

    monkeypatch.setattr(gd, "get_weather", fake_weather)

    place = {"city": "Kent", "state": "Ohio"}
    result = gd.get_game_weather(place, date(2026, 10, 1))

    assert result["summary"] == "Clear"
    assert result["icon"] == "wb_sunny"


# Test an unknown weather code
def test_unknown_weather(monkeypatch):
    monkeypatch.setattr(
        gd, "get_weather",
        lambda city, state, day: {
            "weather": [{"weather_code": 999}]
        }
    )

    result = gd.get_game_weather(
        {"city": "Kent", "state": "Ohio"}, date(2026, 10, 1)
    )
    assert result["summary"] == "Unknown"


# Test getting game information
def test_get_info(monkeypatch):
    data = {
        "contests": [{
            "hasStartTime": True,
            "startTime": "14:00",
            "teams": [
                {"teamId": gd.OUR_TEAM_ID, "nameShort": "Kent"},
                {"teamId": 123, "nameShort": "Akron"}
            ]
        }]
    }

    monkeypatch.setattr(gd, "fetch", lambda path: data)

    result = gd.get_info(1)
    assert result["our_name"] == "Kent"
    assert result["their_name"] == "Akron"
    assert result["start_time"] == "2:00 PM"


# Test goal information
def test_get_goals(monkeypatch):
    data = {
        "periods": [{
            "summary": [{
                "teamId": gd.OUR_TEAM_ID,
                "time": "10:00",
                "scoreText": "John Smith (Goal)",
                "homeScore": 1,
                "visitScore": 0
            }]
        }]
    }

    monkeypatch.setattr(gd, "fetch", lambda path: data)

    result = gd.get_goals(1, True)
    assert len(result) == 1
    assert result[0]["ours"] is True
    assert result[0]["score"] == (1, 0)

    away_result = gd.get_goals(1, False)
    assert away_result[0]["score"] == (0, 1)


# Test empty goal information
def test_empty_goals(monkeypatch):
    monkeypatch.setattr(gd, "fetch", lambda path: {})
    assert gd.get_goals(1, True) == []


# Test team statistics
def test_team_stats(monkeypatch):
    data = {
        "teamBoxscore": [
            {
                "teamId": gd.OUR_TEAM_ID,
                "teamStats": {"shots": 10}
            },
            {
                "teamId": 123,
                "teamStats": {"shots": 5}
            }
        ]
    }

    monkeypatch.setattr(gd, "fetch", lambda path: data)

    result = gd.get_team_stats(1)
    assert ("Shots", 10, 5) in result


# Test the API helper
def test_fetch(monkeypatch):
    def fake_api(path, sleep):
        assert path == "/game/1"
        assert callable(sleep)
        return {"ok": True}

    monkeypatch.setattr(gd, "get_api_data", fake_api)
    assert gd.fetch("/game/1") == {"ok": True}


# Test that sleep is limited to one second
def test_short_sleep(monkeypatch):
    calls = []
    monkeypatch.setattr(gd.time, "sleep", lambda n: calls.append(n))

    gd.short_sleep(5)
    assert calls == [1]


# Test game details and caching
def test_game_details_cache(monkeypatch):
    gd.cache.clear()

    monkeypatch.setattr(
        gd, "find_place",
        lambda game: {"city": "Kent", "state": "Ohio"}
    )
    monkeypatch.setattr(gd, "get_info", lambda game_id: {"name": "Game"})
    monkeypatch.setattr(gd, "get_goals", lambda game_id, home: [])
    monkeypatch.setattr(gd, "get_team_stats", lambda game_id: [])
    monkeypatch.setattr(
        gd, "get_game_weather",
        lambda place, day: {"summary": "Clear"}
    )
    monkeypatch.setattr(gd, "get_our_players", lambda game_id: [])

    game = {"game_id": 1, "home": True, "date": date(2026, 10, 1)}

    first = gd.get_game_details(game)
    second = gd.get_game_details(game)

    assert first == second
    assert 1 in gd.cache
    gd.cache.clear()


# Test that failed information is not cached
def test_game_details_failure(monkeypatch):
    gd.cache.clear()

    monkeypatch.setattr(gd, "find_place", lambda game: None)

    def fail(game_id):
        raise ValueError("API error")

    monkeypatch.setattr(gd, "get_info", fail)
    monkeypatch.setattr(gd, "get_goals", lambda game_id, home: [])
    monkeypatch.setattr(gd, "get_team_stats", lambda game_id: [])
    monkeypatch.setattr(gd, "get_our_players", lambda game_id: [])

    result = gd.get_game_details({"game_id": 2})

    assert result["info"] is None
    assert result["goals"] == []
    assert 2 not in gd.cache
    gd.cache.clear()


# Create a small temporary database for testing
def make_database(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    db = sqlite3.connect(path)

    db.executescript("""
        CREATE TABLE Teams (
            team_id INTEGER,
            team_name TEXT
        );

        CREATE TABLE Games (
            game_id INTEGER,
            game_date TEXT,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_score INTEGER,
            away_score INTEGER,
            location TEXT
        );

        CREATE TABLE Players (
            player_id INTEGER,
            first_name TEXT,
            last_name TEXT,
            position TEXT
        );

        CREATE TABLE PlayerGameStats (
            game_id INTEGER,
            team_id INTEGER,
            player_id INTEGER,
            participated INTEGER,
            starter INTEGER,
            minutes_played INTEGER,
            goals INTEGER,
            assists INTEGER,
            shots INTEGER
        );
    """)

    db.executemany(
        "INSERT INTO Teams VALUES (?, ?)",
        [(gd.OUR_TEAM_ID, "Kent"), (123, "Akron")]
    )

    db.execute(
        "INSERT INTO Games VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, "2026-10-05", gd.OUR_TEAM_ID, 123,
         2, 1, "Kent, OH")
    )

    db.execute(
        "INSERT INTO Players VALUES (?, ?, ?, ?)",
        (1, "John", "Smith", "Forward")
    )

    db.execute(
        "INSERT INTO PlayerGameStats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, gd.OUR_TEAM_ID, 1, 1, 1, 90, 2, 0, 4)
    )

    db.commit()
    db.close()

    monkeypatch.setattr(gd, "DB_PATH", str(path))
    return path


# Test reading teams from the database
def test_get_teams(tmp_path, monkeypatch):
    make_database(tmp_path, monkeypatch)
    assert gd.get_teams() == ["Akron", "Kent"]


# Test getting a team's home venue
def test_home_venue(tmp_path, monkeypatch):
    make_database(tmp_path, monkeypatch)
    assert gd.get_home_venue(gd.OUR_TEAM_ID) == "Kent, OH"
    assert gd.get_home_venue(123) is None


# Test getting players from the database
def test_our_players(tmp_path, monkeypatch):
    make_database(tmp_path, monkeypatch)

    players = gd.get_our_players(1)
    assert len(players) == 1
    assert players[0]["first_name"] == "John"
    assert players[0]["goals"] == 2


# Test games by month
def test_get_games_by_month(tmp_path, monkeypatch):
    path = make_database(tmp_path, monkeypatch)

    games = gd.get_games(year=2026, month=10, db_path=path)

    assert len(games) == 1
    assert games[0]["opponent"] == "Akron"
    assert games[0]["home"] is True
    assert games[0]["score"] == (2, 1)


# Test getting recent games
def test_get_recent_games(tmp_path, monkeypatch):
    path = make_database(tmp_path, monkeypatch)

    games = gd.get_games(db_path=path, games=5)

    assert len(games) == 1
    assert games[0]["game_id"] == 1
