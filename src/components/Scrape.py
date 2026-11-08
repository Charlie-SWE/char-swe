import argparse
import http.client
import json
import re
import sqlite3
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "gaffer.db"
SCHEMA_PATH = ROOT / "data" / "schema.sql"

API_HOST = "ncaa-api.henrygd.me"
SEASON = 2025


# API


RETRY_DELAYS = (2, 5, 15)  # seconds between attempts


class TemporaryAPIError(RuntimeError):
    pass


def _request(path):
    conn = http.client.HTTPSConnection(API_HOST, timeout=20)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        body = response.read().decode()
    except (OSError, http.client.HTTPException) as exc:
        raise TemporaryAPIError(f"{exc}: {path}") from exc
    finally:
        conn.close()

    if response.status == 429 or response.status >= 500:
        raise TemporaryAPIError(
            f"API request failed ({response.status}): {path}"
        )
    if response.status != 200:
        raise RuntimeError(
            f"API request failed ({response.status}): {path}"
        )
    return json.loads(body)


def get_api_data(path, sleep=time.sleep):
    """GET a path, retrying busy-server and network errors."""
    for delay in RETRY_DELAYS:
        try:
            return _request(path)
        except TemporaryAPIError:
            sleep(delay)
    return _request(path)


# small helpers


def as_int(value):
    try:
        return int(value) if value not in (None, "") else 0
    except TypeError, ValueError:
        return 0


def as_jersey(value):
    try:
        return (
            int(value) if value not in (None, "") else None
        )
    except TypeError, ValueError:
        return None


def name_key(first, last):
    """'  FARRINGTON ' and 'Farrington' give the same key."""
    return (
        " ".join(first.split()).casefold(),
        " ".join(last.split()).casefold(),
    )


def is_all_caps(first, last):
    return f"{first}{last}".isupper()


# database setup


def ensure_schema(db):
    """Create any missing tables from data/schema.sql."""
    schema = SCHEMA_PATH.read_text()
    schema = re.sub(
        r"(?i)\bcreate table\b",
        "CREATE TABLE IF NOT EXISTS",
        schema,
    )
    db.executescript(schema)


def game_count(db):
    return db.execute(
        "SELECT COUNT(*) FROM Games"
    ).fetchone()[0]


# players


def load_player_index(db):
    """(team_id, first_key, last_key) -> player_id."""
    index = {}
    rows = db.execute(
        "SELECT DISTINCT s.team_id, p.player_id,"
        " p.first_name, p.last_name"
        " FROM Players p JOIN PlayerGameStats s"
        " ON s.player_id = p.player_id"
        " ORDER BY p.player_id"
    )
    for team_id, player_id, first, last in rows:
        index.setdefault(
            (team_id, *name_key(first, last)), player_id
        )
    return index


def fill_in_player(
    db, player_id, first, last, position, jersey
):
    """Fill blanks on an existing player; prefer 'Smith' to 'SMITH'."""
    db.execute(
        "UPDATE Players SET"
        " position = COALESCE(position, ?),"
        " jersey_number = COALESCE(jersey_number, ?)"
        " WHERE player_id = ?",
        (position, jersey, player_id),
    )
    if not is_all_caps(first, last):
        db.execute(
            "UPDATE Players SET first_name = ?, last_name = ?"
            " WHERE player_id = ?"
            " AND first_name || last_name"
            " = UPPER(first_name || last_name)",
            (first, last, player_id),
        )


def get_or_create_player(
    db,
    index,
    pending,
    team_id,
    first,
    last,
    position,
    jersey,
):
    """Return (player_id, created).

    New players go in `pending` until the game's transaction
    commits, so a failed game can't leave bad ids in `index`.
    """
    key = (team_id, *name_key(first, last))
    player_id = index.get(key) or pending.get(key)
    if player_id is not None:
        fill_in_player(
            db, player_id, first, last, position, jersey
        )
        return player_id, False

    cursor = db.execute(
        "INSERT INTO Players"
        " (first_name, last_name, position, jersey_number)"
        " VALUES (?, ?, ?, ?)",
        (first, last, position, jersey),
    )
    pending[key] = cursor.lastrowid
    return cursor.lastrowid, True


def dedupe_players(db):
    """Merge player rows that are the same person on the same team.

    Each group keeps its lowest player_id; stats from the other
    rows move onto it. Returns how many rows were merged away.
    """
    rows = db.execute(
        "SELECT DISTINCT s.team_id, p.player_id,"
        " p.first_name, p.last_name"
        " FROM Players p JOIN PlayerGameStats s"
        " ON s.player_id = p.player_id"
    ).fetchall()

    # Union-find: a player who played for two teams can link
    # two groups together.
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    first_seen = {}
    for team_id, player_id, first, last in rows:
        key = (team_id, *name_key(first, last))
        if key not in first_seen:
            first_seen[key] = player_id
            continue
        a, b = find(first_seen[key]), find(player_id)
        if a != b:
            parent[max(a, b)] = min(a, b)

    duplicates = sorted(p for p in parent if find(p) != p)

    with db:
        for dup in duplicates:
            keep = find(dup)
            db.execute(
                "UPDATE OR IGNORE PlayerGameStats"
                " SET player_id = ? WHERE player_id = ?",
                (keep, dup),
            )
            # Anything left would be the same game twice.
            db.execute(
                "DELETE FROM PlayerGameStats WHERE player_id = ?",
                (dup,),
            )
            first, last, position, jersey = db.execute(
                "SELECT first_name, last_name, position,"
                " jersey_number FROM Players WHERE player_id = ?",
                (dup,),
            ).fetchone()
            fill_in_player(
                db, keep, first, last, position, jersey
            )
            db.execute(
                "DELETE FROM Players WHERE player_id = ?",
                (dup,),
            )
    return len(duplicates)


# games


def import_game(
    db, index, game_id, game, fetch=get_api_data
):
    """Save one game. Returns (players_added, stats_added)."""
    game_id = str(game_id)
    game_stats = fetch(f"/game/{game_id}/boxscore")
    game_info = fetch(f"/game/{game_id}")

    teams = {
        str(team["teamId"]): team
        for team in game_stats.get("teams", [])
        if team.get("teamId") is not None
    }
    home_team = next(
        (t for t in teams.values() if t.get("isHome")), None
    )
    away_team = next(
        (t for t in teams.values() if not t.get("isHome")),
        None,
    )
    if not home_team or not away_team:
        raise ValueError(
            "Could not identify both teams in the box score."
        )

    contests = game_info.get("contests") or []
    location_data = (contests[0] if contests else {}).get(
        "location"
    ) or {}
    location = (
        ", ".join(
            part
            for part in (
                location_data.get("venue"),
                location_data.get("city"),
                location_data.get("stateUsps"),
            )
            if part
        )
        or None
    )
    game_date = (
        datetime.strptime(game.get("startDate"), "%m/%d/%Y")
        .date()
        .isoformat()
    )

    players_added = 0
    stats_added = 0
    pending = {}

    with db:  # one transaction per game: all or nothing
        for team in teams.values():
            db.execute(
                "INSERT OR IGNORE INTO Teams (team_id, team_name)"
                " VALUES (?, ?)",
                (
                    int(team["teamId"]),
                    team.get("nameFull")
                    or team.get("name")
                    or "Unknown",
                ),
            )

        db.execute(
            "INSERT OR IGNORE INTO Games (game_id, game_date,"
            " home_team_id, away_team_id, location,"
            " home_score, away_score, weather)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
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
                first = " ".join(
                    (player.get("firstName") or "").split()
                )
                last = " ".join(
                    (player.get("lastName") or "").split()
                )
                if not first or not last:
                    continue

                player_id, created = get_or_create_player(
                    db,
                    index,
                    pending,
                    team_id,
                    first,
                    last,
                    player.get("position") or None,
                    as_jersey(player.get("number")),
                )
                players_added += created

                penalties = player.get("penalties") or {}
                cursor = db.execute(
                    "INSERT OR IGNORE INTO PlayerGameStats ("
                    " player_id, game_id, team_id,"
                    " goals, assists, minutes_played,"
                    " shots, shots_on_goal,"
                    " penalty_shot_goals, penalty_shot_attempts,"
                    " fouls, yellow_cards, red_cards,"
                    " saves, goals_against,"
                    " starter, participated)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,"
                    " ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        player_id,
                        int(game_id),
                        team_id,
                        as_int(player.get("goals")),
                        as_int(player.get("assists")),
                        float(
                            player.get("minutesPlayed") or 0
                        ),
                        as_int(player.get("shots")),
                        as_int(player.get("shotsOnGoal")),
                        as_int(
                            player.get("penaltyShotGoals")
                        ),
                        as_int(
                            player.get(
                                "penaltyShotAttempts"
                            )
                        ),
                        as_int(penalties.get("fouls")),
                        as_int(
                            penalties.get("yellowCards")
                        ),
                        as_int(penalties.get("redCards")),
                        as_int(player.get("saves")),
                        as_int(player.get("goalsAllowed")),
                        int(bool(player.get("starter"))),
                        int(
                            bool(player.get("participated"))
                        ),
                    ),
                )
                stats_added += cursor.rowcount

    index.update(pending)  # only after the commit succeeded
    return players_added, stats_added


def scrape_season(db, season=SEASON, fetch=get_api_data):
    schedule = fetch(
        f"/schedule-alt/soccer-women/d1/{season}"
    )
    games = (
        (schedule.get("data") or {})
        .get("schedules", {})
        .get("games", [])
    )
    dates = sorted(
        {
            g["contestDate"]
            for g in games
            if g.get("contestDate")
        },
        key=lambda d: datetime.strptime(d, "%m/%d/%Y"),
    )
    if not dates:
        print("No schedule dates were returned.")
        return False

    print(
        f"Found {len(dates)} scheduled dates for {season}."
    )

    saved = {
        str(row[0])
        for row in db.execute("SELECT game_id FROM Games")
    }
    index = load_player_index(db)
    seen = set()
    imported = already_saved = skipped = failed_dates = 0
    new_players = new_stats = 0

    for date in dates:
        try:
            date_url = datetime.strptime(
                date, "%m/%d/%Y"
            ).strftime("%Y/%m/%d")
            scoreboard = fetch(
                f"/scoreboard/soccer-women/d1/{date_url}/all-conf"
            )
        except Exception as exc:
            print(f"[DATE ERROR] {date}: {exc}")
            failed_dates += 1
            continue

        day_games = scoreboard.get("games", [])
        print(f"{date}: {len(day_games)} games found.")

        for entry in day_games:
            game = entry.get("game", {})
            game_id = str(game.get("gameID") or "")
            if not game_id or game_id in seen:
                continue
            seen.add(game_id)
            if game_id in saved:
                already_saved += 1
                continue

            try:
                players, stats = import_game(
                    db, index, game_id, game, fetch
                )
                new_players += players
                new_stats += stats
                imported += 1
            except Exception as exc:
                skipped += 1
                print(f"[SKIPPED] Game {game_id}: {exc}")

    print("\nSeason import finished.")
    print(f"Unique games found: {len(seen)}")
    print(f"Already in database: {already_saved}")
    print(f"Games imported: {imported}")
    print(f"Games skipped or unavailable: {skipped}")
    print(f"Date requests that failed: {failed_dates}")
    print(f"New players inserted: {new_players}")
    print(f"New player-stat rows inserted: {new_stats}")
    # Complete = every date was fetched. Individual games the
    # API has no box score for are skipped and don't count.
    return failed_dates == 0


def is_complete(db):
    """True once a full season download has finished."""
    return (
        db.execute("PRAGMA user_version").fetchone()[0] >= 1
    )


def mark_complete(db):
    db.execute("PRAGMA user_version = 1")


def prepare_database(db_path=DB_PATH):
    """Create any missing tables.

    Returns True if the season still needs downloading.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as db:
        ensure_schema(db)
        return not is_complete(db)


def fill_database(
    db_path=DB_PATH, fetch=get_api_data, update=False
):
    """Download the season unless that's already been done.

    An unfinished download (e.g. the app was closed partway)
    picks up where it left off, since saved games are skipped.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as db:
        ensure_schema(db)
        db.execute("PRAGMA foreign_keys = ON")

        merged = dedupe_players(db)
        if merged:
            print(f"Merged {merged} duplicate player rows.")

        if is_complete(db) and not update:
            print(
                f"Database already has {game_count(db)} games."
                " Run with --update to fetch missing games."
            )
            return

        if scrape_season(db, fetch=fetch):
            mark_complete(db)
        else:
            print(
                "Download incomplete; it will continue"
                " on the next run."
            )
        print(f"Database: {db_path}")


def main(argv=None, db_path=DB_PATH, fetch=get_api_data):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update",
        action="store_true",
        help="fetch games not yet in the database",
    )
    args = parser.parse_args(argv)
    fill_database(db_path, fetch=fetch, update=args.update)


if __name__ == "__main__":
    main()
