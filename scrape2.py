import http.client
import json
import sqlite3
from pathlib import Path
from datetime import datetime

API_HOST = "ncaa-api.henrygd.me"
SEASON = 2025
DB_PATH = Path(__file__).parent / "data" / "gaffer.db"


def get_api_data(path):
    conn = http.client.HTTPSConnection(API_HOST, timeout=20)

    try:
        conn.request("GET", path)
        response = conn.getresponse()
        body = response.read().decode()

        if response.status != 200:
            raise RuntimeError(
                f"API request failed ({response.status}): {path}"
            )

        return json.loads(body)
    finally:
        conn.close()


def as_int(value):
    try:
        return int(value) if value not in (None, "") else 0
    except (TypeError, ValueError):
        return 0


def import_game(game_id, game):
    game_id = str(game_id)

    game_stats = get_api_data(f"/game/{game_id}/boxscore")
    game_score = get_api_data(f"/game/{game_id}")

    teams = {
        str(team["teamId"]): team
        for team in game_stats.get("teams", [])
        if team.get("teamId") is not None
    }
    home_team = next(
        (team for team in teams.values() if team.get("isHome")), None
    )
    away_team = next(
        (team for team in teams.values() if not team.get("isHome")), None
    )

    if not home_team or not away_team:
        raise ValueError("Could not identify both teams in the box score.")

    contests = game_score.get("contests") or []
    contest = contests[0] if contests else {}
    location_data = contest.get("location") or {}
    location = ", ".join(
        part for part in (
            location_data.get("venue"),
            location_data.get("city"),
            location_data.get("stateUsps"),
        ) if part
    ) or None

    date = game.get("startDate")
    game_date = datetime.strptime(date, "%m/%d/%Y").date().isoformat()

    players_added = 0
    stats_added = 0

    with sqlite3.connect(DB_PATH) as db:
        db.execute("PRAGMA foreign_keys = ON")

        for team in teams.values():
            db.execute(
                """
                insert or ignore into Teams (team_id, team_name)
                values (?, ?)
                """,
                (
                    int(team["teamId"]),
                    team.get("nameFull") or team.get("name") or "Unknown",
                ),
            )

        db.execute(
            """
            insert or ignore into Games (
                game_id, game_date, home_team_id, away_team_id,
                location, home_score, away_score, weather
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(game_id),
                game_date,
                int(home_team["teamId"]),
                int(away_team["teamId"]),
                location,
                as_int(game.get("home", {}).get("score")),
                as_int(game.get("away", {}).get("score")),
                None,
            ),
        )

        for team_box in game_stats.get("teamBoxscore", []):
            team_id = as_int(team_box.get("teamId"))

            for player in team_box.get("playerStats", []):
                first = (player.get("firstName") or "").strip()
                last = (player.get("lastName") or "").strip()

                if not first or not last:
                    continue

                position = player.get("position") or None
                jersey_value = player.get("number")
                try:
                    jersey = int(jersey_value) if jersey_value not in (None, "") else None
                except (TypeError, ValueError):
                    jersey = None

                existing = db.execute(
                    """
                    select player_id from Players
                    where first_name = ? and last_name = ?
                      and position is ? and jersey_number is ?
                    """,
                    (first, last, position, jersey),
                ).fetchone()

                if existing:
                    player_id = existing[0]
                else:
                    cursor = db.execute(
                        """
                        insert into Players
                            (first_name, last_name, position, jersey_number)
                        values (?, ?, ?, ?)
                        """,
                        (first, last, position, jersey),
                    )
                    player_id = cursor.lastrowid
                    players_added += 1

                penalties = player.get("penalties") or {}

                before = db.total_changes
                db.execute(
                    """
                    insert or ignore into PlayerGameStats (
                        player_id, game_id, team_id,
                        goals, assists, minutes_played, shots, shots_on_goal,
                        penalty_shot_goals, penalty_shot_attempts,
                        fouls, yellow_cards, red_cards, saves, goals_against,
                        starter, participated
                    )
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        player_id,
                        int(game_id),
                        team_id,
                        as_int(player.get("goals")),
                        as_int(player.get("assists")),
                        float(player.get("minutesPlayed") or 0),
                        as_int(player.get("shots")),
                        as_int(player.get("shotsOnGoal")),
                        as_int(player.get("penaltyShotGoals")),
                        as_int(player.get("penaltyShotAttempts")),
                        as_int(penalties.get("fouls")),
                        as_int(penalties.get("yellowCards")),
                        as_int(penalties.get("redCards")),
                        as_int(player.get("saves")),
                        as_int(player.get("goalsAllowed")),
                        int(bool(player.get("starter"))),
                        int(bool(player.get("participated"))),
                    ),
                )
                if db.total_changes > before:
                    stats_added += 1

    return players_added, stats_added


def main():
    schedule = get_api_data(f"/schedule-alt/soccer-women/d1/{SEASON}")
    games = (
        schedule.get("data", {})
        .get("schedules", {})
        .get("games", [])
    )

    if not games:
        print("No schedule dates were returned.")
        return

    dates = sorted({
        x["contestDate"]
        for x in games
        if x.get("contestDate")
    })

    print(f"Found {len(dates)} scheduled dates for {SEASON}.")

    games_seen = set()
    imported = 0
    skipped = 0
    failed = 0
    new_players = 0
    new_stats = 0

    for date in dates:
        try:
            date_url = datetime.strptime(
                date, "%m/%d/%Y"
            ).strftime("%Y/%m/%d")
            schedule = get_api_data(
                f"/scoreboard/soccer-women/d1/{date_url}/all-conf"
            )
        except Exception as exc:
            print(f"[DATE ERROR] {date}: {exc}")
            failed += 1
            continue

        games = schedule.get("games", [])
        print(f"{date}: {len(games)} games found.")

        for x in games:
            game = x.get("game", {})
            game_id = str(game.get("gameID") or "")

            if not game_id or game_id in games_seen:
                continue
            games_seen.add(game_id)

            try:
                players_added, stats_added = import_game(game_id, game)
                new_players += players_added
                new_stats += stats_added
                imported += 1
            except Exception as exc:
                skipped += 1
                print(f"[SKIPPED] Game {game_id}: {exc}")

    print("\nSeason import finished.")
    print(f"Unique games found: {len(games_seen)}")
    print(f"Games imported: {imported}")
    print(f"Games skipped or unavailable: {skipped}")
    print(f"Date requests that failed: {failed}")
    print(f"New players inserted: {new_players}")
    print(f"New player-stat rows inserted: {new_stats}")
    print(f"Database: {DB_PATH}")


if __name__ == "__main__":
    main()
