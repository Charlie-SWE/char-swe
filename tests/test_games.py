import calendar
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from src.services.games import (
    build_calendar_html,
    game_label,
    latest_game_month,
    month_bounds,
    result_letter,
    shift_month,
    team_games_in_month,
)

SCHEMA = (
    Path(__file__).parent.parent / "data" / "schema.sql"
).read_text()

KENT = 1


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA)
    c.executemany(
        "INSERT INTO Teams VALUES (?, ?)",
        [
            (1, "Kent State"),
            (2, "Akron"),
            (3, "Texas A&M"),
            (4, "Ohio"),
        ],
    )
    c.executemany(
        "INSERT INTO Games (game_id, game_date, home_team_id,"
        " away_team_id, home_score, away_score)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [
            (10, "2025-08-31", 1, 4, 9, 9),
            (11, "2025-09-01", 1, 2, 2, 1),
            (12, "2025-09-14", 3, 1, 3, 0),
            (13, "2025-09-30", 1, 4, 1, 1),
            (14, "2025-10-01", 2, 1, 0, 2),
            (15, "2025-09-20", 2, 4, 5, 5),
        ],
    )
    yield c
    c.close()


def test_month_bounds_normal_and_december():
    assert month_bounds(2025, 9) == (
        "2025-09-01",
        "2025-10-01",
    )
    assert month_bounds(2025, 12) == (
        "2025-12-01",
        "2026-01-01",
    )


@pytest.mark.parametrize(
    "start, step, expected",
    [
        ((2025, 9), 1, (2025, 10)),
        ((2025, 12), 1, (2026, 1)),
        ((2026, 1), -1, (2025, 12)),
        ((2026, 11), -14, (2025, 9)),
    ],
)
def test_shift_month(start, step, expected):
    assert shift_month(*start, step) == expected


def test_only_this_month_and_this_team(conn):
    games = team_games_in_month(conn, KENT, 2025, 9)
    assert sorted(games) == [1, 14, 30]


def test_home_and_away_are_from_the_teams_side(conn):
    games = team_games_in_month(conn, KENT, 2025, 9)
    home = games[1][0]
    away = games[14][0]
    assert home["home"] is True
    assert home["opponent"] == "Akron"
    assert (home["team_score"], home["opponent_score"]) == (
        2,
        1,
    )
    assert away["home"] is False
    assert away["opponent"] == "Texas A&M"
    assert (away["team_score"], away["opponent_score"]) == (
        0,
        3,
    )


def test_month_with_no_games(conn):
    assert team_games_in_month(conn, KENT, 2026, 11) == {}


def test_latest_game_month(conn):
    assert latest_game_month(
        conn, KENT, date(2026, 11, 1)
    ) == (
        2025,
        10,
    )
    assert latest_game_month(
        conn, KENT, date(2025, 9, 2)
    ) == (
        2025,
        9,
    )
    assert (
        latest_game_month(conn, KENT, date(2020, 1, 1))
        is None
    )


@pytest.mark.parametrize(
    "scores, letter",
    [
        ((2, 1), "W"),
        ((0, 3), "L"),
        ((1, 1), "T"),
        ((None, 1), ""),
    ],
)
def test_result_letter(scores, letter):
    assert result_letter(*scores) == letter


def test_past_game_label_shows_result(conn):
    game = team_games_in_month(conn, KENT, 2025, 9)[1][0]
    assert game_label(game, date(2025, 12, 1)) == (
        "vs Akron <b>W 2-1</b>"
    )


def test_upcoming_game_label_has_no_score(conn):
    game = team_games_in_month(conn, KENT, 2025, 9)[14][0]
    assert (
        game_label(game, date(2025, 9, 1))
        == "@ Texas A&amp;M"
    )


def test_todays_game_has_no_score_yet(conn):
    game = team_games_in_month(conn, KENT, 2025, 9)[1][0]
    assert game_label(game, date(2025, 9, 1)) == "vs Akron"


def test_past_game_without_scores_has_no_score(conn):
    game = dict(
        team_games_in_month(conn, KENT, 2025, 9)[1][0]
    )
    game["team_score"] = None
    game["opponent_score"] = None
    label = game_label(game, date(2025, 12, 1))
    assert label == "vs Akron"
    assert "None" not in label


def test_past_game_with_one_score_missing_has_no_score(
    conn,
):
    game = dict(
        team_games_in_month(conn, KENT, 2025, 9)[1][0]
    )
    game["opponent_score"] = None
    assert game_label(game, date(2025, 12, 1)) == "vs Akron"


def cell(html, day):
    marker = f'<div class="day-number">{day}</div>'
    start = html.rindex("<td", 0, html.index(marker))
    return html[start : html.index("</td>", start)]


def test_game_days_get_a_dot(conn):
    games = team_games_in_month(conn, KENT, 2025, 9)
    html = build_calendar_html(
        2025, 9, games, date(2025, 9, 10)
    )
    assert html.count('class="event-dot"') == 3
    assert 'class="event-dot"' in cell(html, 14)
    assert 'class="event-dot"' not in cell(html, 2)


def test_no_emoji_anywhere(conn):
    games = team_games_in_month(conn, KENT, 2025, 9)
    html = build_calendar_html(
        2025, 9, games, date(2025, 9, 10)
    )
    assert all(ord(ch) < 0x2000 for ch in html)


def test_past_and_upcoming_games_look_different(conn):
    games = team_games_in_month(conn, KENT, 2025, 9)
    html = build_calendar_html(
        2025, 9, games, date(2025, 9, 10)
    )
    assert 'class="past-game"' in cell(html, 1)
    assert 'class="game"' in cell(html, 14)
    assert "W 2-1" in cell(html, 1)
    assert "0-3" not in cell(html, 14)


def test_today_is_marked(conn):
    html = build_calendar_html(
        2025, 9, {}, date(2025, 9, 10)
    )
    assert html.count('class="today"') == 1
    assert 'class="today"' in cell(html, 10)
    assert "Today" in cell(html, 10)


def test_today_in_another_month_is_not_marked():
    html = build_calendar_html(
        2025, 9, {}, date(2026, 11, 1)
    )
    assert "today" not in html


def test_game_today_is_today_and_upcoming(conn):
    games = team_games_in_month(conn, KENT, 2025, 9)
    html = build_calendar_html(
        2025, 9, games, date(2025, 9, 14)
    )
    assert 'class="today game"' in cell(html, 14)


def test_every_day_of_month_appears():
    html = build_calendar_html(
        2025, 2, {}, date(2026, 1, 1)
    )
    assert html.count('class="day-number"') == 28
    assert html.count("<tr>") == 1 + len(
        calendar.monthcalendar(2025, 2)
    )
