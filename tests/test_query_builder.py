import sqlite3
from pathlib import Path

import pytest

from src.services.query_builder import (
    COLUMNS,
    POSITION_GROUPS,
    PlayerFilters,
    build_player_query,
    list_teams,
    run_query,
)

SCHEMA = (
    Path(__file__).parent.parent / "data" / "schema.sql"
).read_text()


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA)
    c.executemany(
        "INSERT INTO Teams VALUES (?, ?)",
        [(1, "Kent State"), (2, "Akron")],
    )
    c.executemany(
        "INSERT INTO Players VALUES (?, ?, ?, ?, ?)",
        [
            (1, "Emma", "Klein", "GK", 0),
            (2, "Samantha", "Miller", "MIDFIELDER", 2),
            (3, "Kiyomi", "McCausland", "F", 7),
            (4, "Ava", "Todd", "def", 9),
            (5, "Leah", "Shaffer", "GOALKEEPER", 1),
            (6, "Pat", "Unknown", None, 30),
        ],
    )
    c.executemany(
        "INSERT INTO Games (game_id, game_date,"
        " home_team_id, away_team_id) VALUES (?, ?, ?, ?)",
        [(1, "2026-09-01", 1, 2), (2, "2026-09-08", 2, 1)],
    )
    stats = [
        (1, 1, 1, 0, 0),
        (2, 1, 1, 1, 2),
        (2, 2, 1, 1, 0),
        (3, 1, 1, 3, 1),
        (4, 1, 2, 0, 1),
    ]
    c.executemany(
        "INSERT INTO PlayerGameStats (player_id, game_id,"
        " team_id, goals, assists, starter, participated)"
        " VALUES (?, ?, ?, ?, ?, 1, 1)",
        stats,
    )
    yield c
    c.close()


def rows_for(conn, **kwargs):
    sql, params = build_player_query(
        PlayerFilters(**kwargs)
    )
    return run_query(conn, sql, params)


def test_exact_translation():
    sql, params = build_player_query(
        PlayerFilters(
            columns=["first_name", "goals"],
            team_id=1,
            position="GK",
            order_by="goals",
            descending=True,
            limit=5,
        )
    )
    assert sql == (
        "SELECT p.first_name AS first_name, "
        "COALESCE(SUM(s.goals), 0) AS goals "
        "FROM Players p LEFT JOIN PlayerGameStats s "
        "ON s.player_id = p.player_id "
        "WHERE p.player_id IN (SELECT player_id "
        "FROM PlayerGameStats WHERE team_id = ?) "
        "AND p.position IN (?, ?, ?) "
        "GROUP BY p.player_id "
        "ORDER BY COALESCE(SUM(s.goals), 0) DESC LIMIT ?"
    )
    assert params == [1, "GK", "GOALKEEPER", "gk", 5]


def test_no_filters_means_no_where():
    sql, params = build_player_query(PlayerFilters())
    assert "WHERE" not in sql
    assert "LIMIT" not in sql
    assert params == []


def test_blank_name_is_ignored():
    sql, _ = build_player_query(PlayerFilters(name="   "))
    assert "LIKE" not in sql


def test_values_are_parameterized_not_inlined():
    sql, params = build_player_query(
        PlayerFilters(name="Emma", team_id=42, position="F")
    )
    assert "Emma" not in sql
    assert "42" not in sql
    assert "FORWARD" not in sql
    assert "%Emma%" in params


def test_like_wildcards_are_escaped():
    _, params = build_player_query(
        PlayerFilters(name="50%_")
    )
    assert params[0] == "%50\\%\\_%"


def test_only_one_select_statement():
    sql, _ = build_player_query(PlayerFilters())
    assert sql.startswith("SELECT")
    assert ";" not in sql
    assert sqlite3.complete_statement(sql + ";")


@pytest.mark.parametrize(
    "bad",
    [
        {"columns": []},
        {"columns": ["first_name; DROP TABLE Players"]},
        {"order_by": "1; DELETE FROM Players"},
        {"position": "GK' OR '1'='1"},
        {"team_id": "1 OR 1=1"},
        {"limit": 0},
        {"limit": "5"},
    ],
)
def test_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        build_player_query(PlayerFilters(**bad))


@pytest.mark.parametrize("position", list(POSITION_GROUPS))
def test_every_option_compiles_against_schema(
    conn, position
):
    sql, params = build_player_query(
        PlayerFilters(
            columns=list(COLUMNS),
            name="a",
            team_id=1,
            position=position,
            order_by="assists",
        )
    )
    conn.execute("EXPLAIN " + sql, params)


def test_returns_selected_columns_in_order(conn):
    rows = rows_for(conn, columns=["last_name", "goals"])
    assert list(rows[0].keys()) == ["last_name", "goals"]


def test_position_group_matches_messy_values(conn):
    rows = rows_for(
        conn,
        columns=["last_name", "position"],
        position="GK",
    )
    assert {r["last_name"] for r in rows} == {
        "Klein",
        "Shaffer",
    }


def test_unknown_position_includes_null(conn):
    rows = rows_for(
        conn, columns=["last_name"], position="Unknown"
    )
    assert [r["last_name"] for r in rows] == ["Unknown"]


def test_name_search_is_case_insensitive(conn):
    rows = rows_for(
        conn, columns=["last_name"], name="emma k"
    )
    assert [r["last_name"] for r in rows] == ["Klein"]


def test_team_filter(conn):
    rows = rows_for(conn, columns=["last_name"], team_id=2)
    assert [r["last_name"] for r in rows] == ["Todd"]


def test_stat_totals(conn):
    rows = rows_for(
        conn,
        columns=["last_name", "games", "goals", "assists"],
        order_by="player_id",
    )
    by_name = {r["last_name"]: r for r in rows}
    assert by_name["Miller"]["games"] == 2
    assert by_name["Miller"]["goals"] == 2
    assert by_name["Miller"]["assists"] == 2
    assert by_name["Shaffer"]["games"] == 0
    assert by_name["Shaffer"]["goals"] == 0


def test_one_row_per_player(conn):
    rows = rows_for(conn, columns=["player_id"])
    ids = [r["player_id"] for r in rows]
    assert len(ids) == len(set(ids)) == 6


def test_ordering(conn):
    rows = rows_for(
        conn,
        columns=["goals"],
        order_by="goals",
        descending=True,
    )
    goals = [r["goals"] for r in rows]
    assert goals == sorted(goals, reverse=True)
    assert goals[0] == 3


def test_limit(conn):
    assert len(rows_for(conn, limit=2)) == 2


def test_no_limit_returns_every_match(conn):
    assert len(rows_for(conn)) == 6


def test_types(conn):
    rows = rows_for(conn, columns=list(COLUMNS))
    for r in rows:
        assert isinstance(r["first_name"], str)
        assert isinstance(r["jersey_number"], int)
        assert isinstance(r["goals"], int)
        assert r["position"] is None or isinstance(
            r["position"], str
        )


def test_no_match_is_empty_list(conn):
    assert rows_for(conn, name="zzz") == []


def test_injection_attempt_leaves_data_intact(conn):
    rows = rows_for(conn, name="'; DROP TABLE Players; --")
    assert rows == []
    count = conn.execute(
        "SELECT COUNT(*) FROM Players"
    ).fetchone()[0]
    assert count == 6


def test_list_teams(conn):
    assert list_teams(conn) == {2: "Akron", 1: "Kent State"}
