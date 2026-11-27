import sqlite3
import pytest

from src.services.query_builder import (
    PlayerFilters,
    escape_like,
    build_player_query,
    run_query,
    list_teams,
)


def test_escape_like():
    assert escape_like("a%b_c\\d") == "a\\%b\\_c\\\\d"


def test_default_query():
    sql, params = build_player_query(PlayerFilters())

    assert "SELECT" in sql
    assert "FROM Players" in sql
    assert "GROUP BY p.player_id" in sql
    assert "ORDER BY p.last_name ASC" in sql
    assert params == []


def test_name_filter():
    sql, params = build_player_query(
        PlayerFilters(name="John")
    )

    assert "LIKE ?" in sql
    assert params == ["%John%"]


def test_team_filter():
    sql, params = build_player_query(
        PlayerFilters(team_id=1)
    )

    assert "team_id = ?" in sql
    assert params == [1]


def test_position_filter():
    sql, params = build_player_query(
        PlayerFilters(position="GK")
    )

    assert "p.position IN" in sql
    assert params == ["GK", "GOALKEEPER", "gk"]


def test_unknown_position():
    sql, params = build_player_query(
        PlayerFilters(position="Unknown")
    )

    assert "p.position IS NULL" in sql
    assert params == ["n/a"]


def test_descending():
    sql, params = build_player_query(
        PlayerFilters(order_by="goals", descending=True)
    )

    assert "DESC" in sql


def test_limit():
    sql, params = build_player_query(
        PlayerFilters(limit=5)
    )

    assert "LIMIT ?" in sql
    assert params == [5]


def test_multiple_filters():
    sql, params = build_player_query(
        PlayerFilters(name="John", team_id=1, limit=5)
    )

    assert "AND" in sql
    assert params == ["%John%", 1, 5]


def test_empty_columns():
    with pytest.raises(ValueError):
        build_player_query(PlayerFilters(columns=()))


def test_invalid_column():
    with pytest.raises(ValueError):
        build_player_query(
            PlayerFilters(columns=("invalid",))
        )


def test_invalid_limit():
    with pytest.raises(ValueError):
        build_player_query(PlayerFilters(limit=-1))


def test_invalid_team():
    with pytest.raises(ValueError):
        build_player_query(PlayerFilters(team_id="abc"))


def test_invalid_position():
    with pytest.raises(ValueError):
        build_player_query(PlayerFilters(position="abc"))


def test_run_query():
    conn = sqlite3.connect(":memory:")

    result = run_query(conn, "SELECT 1 AS player_id", [])

    assert result == [{"player_id": 1}]

    conn.close()


def test_list_teams():
    conn = sqlite3.connect(":memory:")

    conn.execute(
        "CREATE TABLE Teams (team_id INTEGER, team_name TEXT)"
    )

    conn.execute("INSERT INTO Teams VALUES (1, 'Kent State')")
    conn.execute("INSERT INTO Teams VALUES (2, 'Akron')")

    assert list_teams(conn) == {
        1: "Kent State",
        2: "Akron"
    }

    conn.close()