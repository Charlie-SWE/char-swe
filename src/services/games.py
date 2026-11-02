"""Game dates for the calendar page, read from data/gaffer.db."""

import calendar
import html
import sqlite3
from datetime import date


def month_bounds(year: int, month: int) -> tuple[str, str]:
    """ISO dates for the first day of this month and the next."""
    start = date(year, month, 1)
    end = (
        date(year + 1, 1, 1)
        if month == 12
        else date(year, month + 1, 1)
    )
    return start.isoformat(), end.isoformat()


def shift_month(
    year: int, month: int, step: int
) -> tuple[int, int]:
    index = year * 12 + (month - 1) + step
    return index // 12, index % 12 + 1


def team_games_in_month(
    conn: sqlite3.Connection,
    team_id: int,
    year: int,
    month: int,
) -> dict[int, list[dict]]:
    """Day of month -> that team's games on that day."""
    start, end = month_bounds(year, month)
    rows = conn.execute(
        "SELECT g.game_date, g.home_team_id, g.home_score,"
        " g.away_score, g.location,"
        " home.team_name, away.team_name"
        " FROM Games g"
        " JOIN Teams home ON home.team_id = g.home_team_id"
        " JOIN Teams away ON away.team_id = g.away_team_id"
        " WHERE ? IN (g.home_team_id, g.away_team_id)"
        " AND g.game_date >= ? AND g.game_date < ?"
        " ORDER BY g.game_date, g.game_id",
        (team_id, start, end),
    )
    games: dict[int, list[dict]] = {}
    for (
        game_date,
        home_id,
        home_score,
        away_score,
        location,
        home_name,
        away_name,
    ) in rows:
        is_home = home_id == team_id
        games.setdefault(
            date.fromisoformat(game_date).day, []
        ).append(
            {
                "date": date.fromisoformat(game_date),
                "home": is_home,
                "opponent": (
                    away_name if is_home else home_name
                ),
                "team_score": (
                    home_score if is_home else away_score
                ),
                "opponent_score": (
                    away_score if is_home else home_score
                ),
                "location": location,
            }
        )
    return games


def latest_game_month(
    conn: sqlite3.Connection, team_id: int, before: date
) -> tuple[int, int] | None:
    """(year, month) of the team's last game on or before a date."""
    row = conn.execute(
        "SELECT MAX(game_date) FROM Games"
        " WHERE ? IN (home_team_id, away_team_id)"
        " AND game_date <= ?",
        (team_id, before.isoformat()),
    ).fetchone()
    if not row or row[0] is None:
        return None
    last = date.fromisoformat(row[0])
    return last.year, last.month


def result_letter(team_score, opponent_score) -> str:
    if team_score is None or opponent_score is None:
        return ""
    if team_score > opponent_score:
        return "W"
    if team_score < opponent_score:
        return "L"
    return "T"


def has_score(game: dict, today: date) -> bool:
    """Scores only for games already played that have both scores."""
    return (
        game["date"] < today
        and game["team_score"] is not None
        and game["opponent_score"] is not None
    )


def game_label(game: dict, today: date) -> str:
    where = "vs" if game["home"] else "@"
    text = f"{where} {html.escape(game['opponent'])}"
    if has_score(game, today):
        result = result_letter(
            game["team_score"], game["opponent_score"]
        )
        text += (
            f" <b>{result} {game['team_score']}-"
            f"{game['opponent_score']}</b>"
        )
    return text


def build_calendar_html(
    year: int,
    month: int,
    games_by_day: dict[int, list[dict]],
    today: date,
) -> str:
    """Month table. Cells get 'today', 'game', 'past-game' classes."""
    out = ['<table class="calendar">', "<tr>"]
    for day_name in [
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat",
        "Sun",
    ]:
        out.append(f"<th>{day_name}</th>")
    out.append("</tr>")

    for week in calendar.monthcalendar(year, month):
        out.append("<tr>")
        for day in week:
            if day == 0:
                out.append("<td></td>")
                continue

            this_day = date(year, month, day)
            classes = []
            if this_day == today:
                classes.append("today")
            games = games_by_day.get(day, [])
            if games:
                classes.append(
                    "past-game"
                    if this_day < today
                    else "game"
                )

            out.append(f'<td class="{" ".join(classes)}">')
            out.append(
                f'<div class="day-number">{day}</div>'
            )
            if this_day == today:
                out.append(
                    '<div class="today-tag">Today</div>'
                )
            for game in games:
                out.append(
                    '<div class="game-info">'
                    '<span class="event-dot"></span> '
                    f"{game_label(game, today)}</div>"
                )
            out.append("</td>")
        out.append("</tr>")

    out.append("</table>")
    return "".join(out)
