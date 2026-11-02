import sqlite3
from contextlib import closing

import pytest

import src.components.Scrape as scrape


@pytest.fixture
def db():
    c = sqlite3.connect(":memory:")
    scrape.ensure_schema(c)
    c.execute("PRAGMA foreign_keys = ON")
    yield c
    c.close()


def player(first, last, goals="0", number=7, position="F"):
    return {
        "firstName": first,
        "lastName": last,
        "position": position,
        "number": number,
        "goals": goals,
        "assists": "1",
        "minutesPlayed": "90",
        "starter": True,
        "participated": True,
        "penalties": {"fouls": "1"},
    }


def fake_api(boxscores):
    """boxscores: game_id -> list of (team_id, [players])."""

    def fetch(path):
        if path.startswith("/schedule-alt/"):
            return {
                "data": {
                    "schedules": {
                        "games": [
                            {"contestDate": "09/08/2025"},
                            {"contestDate": "09/01/2025"},
                        ]
                    }
                }
            }
        if path.startswith("/scoreboard/"):
            day = (
                "09/01/2025"
                if "09/01" in path
                else "09/08/2025"
            )
            return {
                "games": [
                    {"game": game(gid, day)}
                    for gid in boxscores
                    if (gid == "1") == (day == "09/01/2025")
                ]
            }
        game_id = path.split("/")[2]
        if path.endswith("/boxscore"):
            if boxscores[game_id] == "error":
                raise RuntimeError("API down")
            return {
                "teams": [
                    {
                        "teamId": "10",
                        "isHome": True,
                        "nameFull": "Kent State",
                    },
                    {
                        "teamId": "20",
                        "isHome": False,
                        "nameFull": "Akron",
                    },
                ],
                "teamBoxscore": [
                    {
                        "teamId": team_id,
                        "playerStats": players,
                    }
                    for team_id, players in boxscores[
                        game_id
                    ]
                ],
            }
        return {
            "contests": [{"location": {"city": "Kent"}}]
        }

    return fetch


def game(game_id, day="09/01/2025"):
    return {
        "gameID": game_id,
        "startDate": day,
        "home": {"score": "2"},
        "away": {"score": "1"},
    }


def count(db, table):
    return db.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]


# ---------- setup ----------


def test_ensure_schema_is_safe_to_run_twice(db):
    scrape.ensure_schema(db)
    tables = {
        r[0]
        for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {
        "Teams",
        "Players",
        "Games",
        "PlayerGameStats",
    } <= tables


def test_db_path_points_at_project_data_folder():
    assert scrape.DB_PATH.parent.name == "data"
    assert scrape.SCHEMA_PATH.exists()


def test_name_key_ignores_case_and_spacing():
    assert scrape.name_key(
        " ava ", "TODD"
    ) == scrape.name_key("Ava", "Todd")


# ---------- importing without duplicates ----------


def test_same_player_in_two_games_is_one_row(db):
    fetch = fake_api(
        {
            "1": [
                ("10", [player("Ava", "Todd", goals="1")])
            ],
            "2": [
                ("10", [player("AVA", "TODD", goals="2")])
            ],
        }
    )
    index = {}
    scrape.import_game(db, index, "1", game("1"), fetch)
    added, stats = scrape.import_game(
        db, index, "2", game("2"), fetch
    )
    assert (added, stats) == (0, 1)
    assert count(db, "Players") == 1
    assert count(db, "PlayerGameStats") == 2
    total = db.execute(
        "SELECT SUM(goals) FROM PlayerGameStats"
    ).fetchone()[0]
    assert total == 3


def test_prefers_normal_capitalisation(db):
    fetch = fake_api(
        {
            "1": [("10", [player("AVA", "TODD")])],
            "2": [("10", [player("Ava", "Todd")])],
        }
    )
    index = {}
    scrape.import_game(db, index, "1", game("1"), fetch)
    scrape.import_game(db, index, "2", game("2"), fetch)
    assert db.execute(
        "SELECT first_name, last_name FROM Players"
    ).fetchone() == ("Ava", "Todd")


def test_fills_in_missing_jersey(db):
    fetch = fake_api(
        {
            "1": [
                ("10", [player("Ava", "Todd", number=None)])
            ],
            "2": [
                ("10", [player("Ava", "Todd", number=9)])
            ],
        }
    )
    index = {}
    scrape.import_game(db, index, "1", game("1"), fetch)
    scrape.import_game(db, index, "2", game("2"), fetch)
    assert db.execute(
        "SELECT jersey_number FROM Players"
    ).fetchone() == (9,)


def test_same_name_on_different_teams_stays_separate(db):
    fetch = fake_api(
        {
            "1": [
                ("10", [player("Sam", "Lee")]),
                ("20", [player("Sam", "Lee")]),
            ]
        }
    )
    scrape.import_game(db, {}, "1", game("1"), fetch)
    assert count(db, "Players") == 2


def test_importing_same_game_twice_adds_nothing(db):
    fetch = fake_api(
        {"1": [("10", [player("Ava", "Todd")])]}
    )
    index = {}
    scrape.import_game(db, index, "1", game("1"), fetch)
    assert scrape.import_game(
        db, index, "1", game("1"), fetch
    ) == (0, 0)
    assert count(db, "Games") == 1
    assert count(db, "PlayerGameStats") == 1


def test_failed_game_saves_nothing(db):
    good = player("Ava", "Todd")
    bad = player("Mia", "Cleroux")
    bad["minutesPlayed"] = "not a number"  # float() fails
    fetch = fake_api({"1": [("10", [good, bad])]})
    index = {}
    with pytest.raises(ValueError):
        scrape.import_game(db, index, "1", game("1"), fetch)
    assert count(db, "Games") == 0
    assert count(db, "Players") == 0
    assert index == {}


def test_index_finds_players_already_in_database(db):
    fetch = fake_api(
        {
            "1": [("10", [player("Ava", "Todd")])],
            "2": [("10", [player("ava", "todd")])],
        }
    )
    scrape.import_game(db, {}, "1", game("1"), fetch)
    index = scrape.load_player_index(db)
    scrape.import_game(db, index, "2", game("2"), fetch)
    assert count(db, "Players") == 1


# ---------- cleaning up existing duplicates ----------


def seed_duplicates(db):
    db.executemany(
        "INSERT INTO Teams VALUES (?, ?)",
        [(10, "Kent State"), (20, "Akron")],
    )
    db.executemany(
        "INSERT INTO Games (game_id, game_date,"
        " home_team_id, away_team_id) VALUES (?, ?, 10, 20)",
        [
            (1, "2025-09-01"),
            (2, "2025-09-08"),
            (3, "2025-09-15"),
        ],
    )
    db.executemany(
        "INSERT INTO Players VALUES (?, ?, ?, ?, ?)",
        [
            (1, "AVA", "TODD", None, 9),
            (2, "Ava", "Todd", "D", 9),
            (3, "Ava", "Todd", "def", None),
            (4, "Sam", "Lee", "M", 4),  # other team
            (5, "Sam", "Lee", "F", 5),  # this team
        ],
    )
    db.executemany(
        "INSERT INTO PlayerGameStats (player_id, game_id,"
        " team_id, goals, starter, participated)"
        " VALUES (?, ?, ?, ?, 1, 1)",
        [
            (1, 1, 10, 1),
            (2, 2, 10, 2),
            (3, 3, 10, 3),
            (4, 1, 20, 0),
            (5, 2, 10, 1),
        ],
    )
    db.commit()


def test_dedupe_merges_same_player_same_team(db):
    seed_duplicates(db)
    assert scrape.dedupe_players(db) == 2
    assert db.execute(
        "SELECT player_id, first_name, last_name, position,"
        " jersey_number FROM Players WHERE player_id = 1"
    ).fetchone() == (1, "Ava", "Todd", "D", 9)
    goals = db.execute(
        "SELECT SUM(goals), COUNT(*) FROM PlayerGameStats"
        " WHERE player_id = 1"
    ).fetchone()
    assert goals == (6, 3)


def test_dedupe_keeps_different_teams_apart(db):
    seed_duplicates(db)
    scrape.dedupe_players(db)
    assert db.execute(
        "SELECT COUNT(*) FROM Players WHERE last_name = 'Lee'"
    ).fetchone() == (2,)


def test_dedupe_keeps_all_stats_and_is_repeatable(db):
    seed_duplicates(db)
    before = count(db, "PlayerGameStats")
    scrape.dedupe_players(db)
    assert count(db, "PlayerGameStats") == before
    assert scrape.dedupe_players(db) == 0
    orphans = db.execute(
        "SELECT COUNT(*) FROM PlayerGameStats WHERE player_id"
        " NOT IN (SELECT player_id FROM Players)"
    ).fetchone()[0]
    assert orphans == 0


# ---------- whole run ----------


def test_main_scrapes_when_empty_then_skips(
    tmp_path, capsys
):
    fetch = fake_api(
        {
            "1": [("10", [player("Ava", "Todd")])],
            "2": [("10", [player("AVA", "TODD")])],
        }
    )
    db_file = tmp_path / "test.db"

    scrape.main([], db_path=db_file, fetch=fetch)
    with closing(sqlite3.connect(db_file)) as c:
        assert count(c, "Games") == 2
        assert count(c, "Players") == 1

    scrape.main([], db_path=db_file, fetch=fetch)
    assert "already has 2 games" in capsys.readouterr().out


def test_update_skips_saved_games(tmp_path, capsys):
    calls = []
    inner = fake_api(
        {"1": [("10", [player("Ava", "Todd")])]}
    )

    def fetch(path):
        calls.append(path)
        return inner(path)

    db_file = tmp_path / "test.db"
    scrape.main([], db_path=db_file, fetch=fetch)
    calls.clear()
    scrape.main(["--update"], db_path=db_file, fetch=fetch)
    assert not any("boxscore" in c for c in calls)
    assert (
        "Already in database: 1" in capsys.readouterr().out
    )


def test_failed_game_is_skipped_not_fatal(db, capsys):
    fetch = fake_api(
        {
            "1": "error",
            "2": [("10", [player("Ava", "Todd")])],
        }
    )
    scrape.scrape_season(db, fetch=fetch)
    out = capsys.readouterr().out
    assert "[SKIPPED] Game 1" in out
    assert count(db, "Games") == 1
