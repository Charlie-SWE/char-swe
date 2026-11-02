"""Download NCAA D1 women's soccer data into data/gaffer.db.

`uv run app.py` runs this in the background on every start:
past seasons are downloaded once, the current season is
refreshed each time (new results and upcoming games).

    uv run app.py --reset-db                         # wipe and re-download everything

By hand:
    uv run python -m src.components.Scrape           # download what's missing
    uv run python -m src.components.Scrape --update  # also re-check finished seasons
    uv run python -m src.components.Scrape --reset   # wipe and re-download everything

Each run:
1. Creates any missing tables from data/schema.sql.
2. Merges duplicate player rows already in the database.
3. For every season from FIRST_SEASON to the current one that
   isn't finished: schedule -> each day's scoreboard -> each game.
   Final games get scores and player stats; games not played
   yet are saved with empty scores so the calendar can show
   them, and are filled in once they're final.

The API gives players no ID, so a player is identified by their
team plus their name, ignoring capitalisation and extra spaces.
"""

import argparse
import http.client
import json
import re
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "gaffer.db"
SCHEMA_PATH = ROOT / "data" / "schema.sql"

API_HOST = "ncaa-api.henrygd.me"
FIRST_SEASON = 2023  # earliest season the API has
SEASON_START_MONTH = (
    7  # from July on, "this season" is this year's
)
SEASON_OVER_AFTER = timedelta(days=7)

# The API's CDN answers 428 when hit too fast (4/s triggered it;
# ~1.3/s ran for 95 minutes without one).
WORKERS = 2
MIN_SECONDS_BETWEEN_REQUESTS = 0.8
RETRY_DELAYS = (
    5,
    30,
    90,
)  # seconds to pause before each retry

TABLES = [
    "PlayerGameStats",
    "Games",
    "Players",
    "Teams",
    "ScrapedSeasons",
]

downloading = (
    threading.Event()
)  # set while a download is running


# ---------- API ----------


class TemporaryAPIError(RuntimeError):
    pass


_rate_lock = threading.Lock()
_next_request_at = 0.0


def _wait_for_turn():
    global _next_request_at
    with _rate_lock:
        now = time.monotonic()
        wait = _next_request_at - now
        _next_request_at = (
            max(now, _next_request_at)
            + MIN_SECONDS_BETWEEN_REQUESTS
        )
    if wait > 0:
        time.sleep(wait)


def _request(path):
    _wait_for_turn()
    conn = http.client.HTTPSConnection(API_HOST, timeout=20)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        body = response.read().decode()
    except (OSError, http.client.HTTPException) as exc:
        raise TemporaryAPIError(f"{exc}: {path}") from exc
    finally:
        conn.close()

    if (
        response.status in (428, 429)
        or response.status >= 500
    ):
        raise TemporaryAPIError(
            f"API request failed ({response.status}): {path}"
        )
    if response.status != 200:
        raise RuntimeError(
            f"API request failed ({response.status}): {path}"
        )
    return json.loads(body)


def pause_all_requests(seconds):
    """Hold back every thread's next request, not just this one."""
    global _next_request_at
    with _rate_lock:
        _next_request_at = max(
            _next_request_at, time.monotonic() + seconds
        )


def get_api_data(path, pause=pause_all_requests):
    """GET a path, retrying rate-limit, server and network errors."""
    for delay in RETRY_DELAYS:
        try:
            return _request(path)
        except TemporaryAPIError:
            pause(delay)
    return _request(path)


# ---------- small helpers ----------


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


def current_season(today):
    return (
        today.year
        if today.month >= SEASON_START_MONTH
        else today.year - 1
    )


def seasons_up_to(today):
    return list(
        range(FIRST_SEASON, current_season(today) + 1)
    )


# ---------- database setup ----------


def ensure_schema(db):
    """Create any missing tables from data/schema.sql."""
    schema = SCHEMA_PATH.read_text()
    schema = re.sub(
        r"(?i)\bcreate table\b",
        "CREATE TABLE IF NOT EXISTS",
        schema,
    )
    db.executescript(schema)


def reset_database(db_path=DB_PATH):
    """Drop every table, then recreate them empty.

    Drops tables instead of deleting the file, so it works even
    while something else has the database open.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as db:
        db.execute("PRAGMA foreign_keys = OFF")
        for table in TABLES:
            db.execute(f"DROP TABLE IF EXISTS {table}")
        db.execute("PRAGMA user_version = 0")
        db.commit()
        db.execute("VACUUM")
        ensure_schema(db)


def game_count(db):
    return db.execute(
        "SELECT COUNT(*) FROM Games"
    ).fetchone()[0]


def finished_seasons(db):
    return {
        row[0]
        for row in db.execute(
            "SELECT season FROM ScrapedSeasons"
        )
    }


def mark_season_finished(db, season):
    with db:
        db.execute(
            "INSERT OR REPLACE INTO ScrapedSeasons"
            " (season, completed_at) VALUES (?, ?)",
            (
                season,
                datetime.now().isoformat(
                    timespec="seconds"
                ),
            ),
        )


def seasons_to_download(db, today, update=False):
    done = set() if update else finished_seasons(db)
    newest_first = sorted(
        seasons_up_to(today), reverse=True
    )
    return [s for s in newest_first if s not in done]


# ---------- players ----------


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


# ---------- games ----------


def is_final(game):
    """Scoreboard entries say 'final' once a game is over."""
    return game.get("gameState", "final") == "final"


def fetch_game(game_id, game, fetch=get_api_data):
    """Network part of a game. Safe to run in a worker thread.

    Final games: box score (teams + player stats) and game info.
    Games not played yet: game info only (it lists both teams).
    """
    game_id = str(game_id)
    if is_final(game):
        return {
            "boxscore": fetch(f"/game/{game_id}/boxscore"),
            "info": fetch(f"/game/{game_id}"),
        }
    return {
        "boxscore": None,
        "info": fetch(f"/game/{game_id}"),
    }


def _location(info):
    contests = info.get("contests") or []
    data = (contests[0] if contests else {}).get(
        "location"
    ) or {}
    return (
        ", ".join(
            part
            for part in (
                data.get("venue"),
                data.get("city"),
                data.get("stateUsps"),
            )
            if part
        )
        or None
    )


def _teams(payload):
    if payload["boxscore"] is not None:
        teams = payload["boxscore"].get("teams", [])
    else:
        contests = payload["info"].get("contests") or []
        teams = (contests[0] if contests else {}).get(
            "teams"
        ) or []
    return {
        str(team["teamId"]): team
        for team in teams
        if team.get("teamId") is not None
    }


def save_game(db, index, game_id, game, payload):
    """Database part of a game. Returns (players_added, stats_added)."""
    game_id = str(game_id)
    final = payload["boxscore"] is not None
    teams = _teams(payload)
    home_team = next(
        (t for t in teams.values() if t.get("isHome")), None
    )
    away_team = next(
        (t for t in teams.values() if not t.get("isHome")),
        None,
    )
    if not home_team or not away_team:
        raise ValueError("Could not identify both teams.")

    game_date = (
        datetime.strptime(game.get("startDate"), "%m/%d/%Y")
        .date()
        .isoformat()
    )
    if final:
        home_score = as_int(
            game.get("home", {}).get("score")
        )
        away_score = as_int(
            game.get("away", {}).get("score")
        )
    else:
        home_score = away_score = None

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
            "INSERT INTO Games (game_id, game_date,"
            " home_team_id, away_team_id, location,"
            " home_score, away_score, weather)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, NULL)"
            " ON CONFLICT (game_id) DO UPDATE SET"
            " game_date = excluded.game_date,"
            " location = COALESCE(excluded.location, location),"
            " home_score = excluded.home_score,"
            " away_score = excluded.away_score",
            (
                int(game_id),
                game_date,
                int(home_team["teamId"]),
                int(away_team["teamId"]),
                _location(payload["info"]),
                home_score,
                away_score,
            ),
        )

        if final:
            for team_box in payload["boxscore"].get(
                "teamBoxscore", []
            ):
                team_id = as_int(team_box.get("teamId"))

                for player in team_box.get(
                    "playerStats", []
                ):
                    first = " ".join(
                        (
                            player.get("firstName") or ""
                        ).split()
                    )
                    last = " ".join(
                        (
                            player.get("lastName") or ""
                        ).split()
                    )
                    if not first or not last:
                        continue

                    player_id, created = (
                        get_or_create_player(
                            db,
                            index,
                            pending,
                            team_id,
                            first,
                            last,
                            player.get("position") or None,
                            as_jersey(player.get("number")),
                        )
                    )
                    players_added += created

                    penalties = (
                        player.get("penalties") or {}
                    )
                    cursor = db.execute(
                        "INSERT OR IGNORE INTO PlayerGameStats ("
                        " player_id, game_id, team_id,"
                        " goals, assists, minutes_played,"
                        " shots, shots_on_goal,"
                        " penalty_shot_goals,"
                        " penalty_shot_attempts,"
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
                                player.get("minutesPlayed")
                                or 0
                            ),
                            as_int(player.get("shots")),
                            as_int(
                                player.get("shotsOnGoal")
                            ),
                            as_int(
                                player.get(
                                    "penaltyShotGoals"
                                )
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
                            as_int(
                                penalties.get("redCards")
                            ),
                            as_int(player.get("saves")),
                            as_int(
                                player.get("goalsAllowed")
                            ),
                            int(
                                bool(player.get("starter"))
                            ),
                            int(
                                bool(
                                    player.get(
                                        "participated"
                                    )
                                )
                            ),
                        ),
                    )
                    stats_added += cursor.rowcount

    index.update(pending)  # only after the commit succeeded
    return players_added, stats_added


def import_game(
    db, index, game_id, game, fetch=get_api_data
):
    """Fetch and save one game. Returns (players_added, stats_added)."""
    payload = fetch_game(game_id, game, fetch)
    return save_game(db, index, game_id, game, payload)


def _season_dates(schedule, season):
    games = (
        (schedule.get("data") or {}).get("schedules") or {}
    ).get("games") or []
    dates = set()
    for g in games:
        try:
            day = datetime.strptime(
                g.get("contestDate") or "", "%m/%d/%Y"
            ).date()
        except ValueError:
            continue
        # The API sometimes answers for a different season.
        if day.year == season:
            dates.add(day)
    return sorted(dates)


def scrape_season(
    db,
    season,
    fetch=get_api_data,
    today=None,
    workers=WORKERS,
    part="all",
):
    """Download one season. Returns True if it's finished for good.

    part="past": today and earlier, newest date first.
    part="future": after today (up to 60 days), soonest first.
    part="all": past, then future.
    """
    today = today or date.today()
    schedule = fetch(
        f"/schedule-alt/soccer-women/d1/{season}"
    )
    dates = _season_dates(schedule, season)
    if not dates:
        print(
            f"[{season}] No schedule dates were returned."
        )
        return season < current_season(today)

    print(f"[{season}] {len(dates)} scheduled dates.")

    done = {
        str(row[0])
        for row in db.execute(
            "SELECT game_id FROM Games"
            " WHERE home_score IS NOT NULL"
        )
    }
    scheduled = {
        str(row[0])
        for row in db.execute(
            "SELECT game_id FROM Games WHERE home_score IS NULL"
        )
    }
    index = load_player_index(db)
    seen = set()
    imported = upcoming = skipped = failed_dates = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        past = [d for d in reversed(dates) if d <= today]
        future = [
            d
            for d in dates
            if today < d <= today + timedelta(days=60)
        ]
        order = {
            "past": past,
            "future": future,
            "all": past + future,
        }[part]

        for day in order:
            try:
                scoreboard = fetch(
                    "/scoreboard/soccer-women/d1/"
                    f"{day:%Y/%m/%d}/all-conf"
                )
            except Exception as exc:
                print(f"[DATE ERROR] {day}: {exc}")
                failed_dates += 1
                continue

            todo = []
            for entry in scoreboard.get("games", []):
                game = entry.get("game", {})
                game_id = str(game.get("gameID") or "")
                if not game_id or game_id in seen:
                    continue
                seen.add(game_id)
                if game_id in done:
                    continue
                if (
                    not is_final(game)
                    and game_id in scheduled
                ):
                    continue
                todo.append((game_id, game))

            def fetch_one(job):
                try:
                    return fetch_game(*job, fetch), None
                except Exception as exc:
                    return None, exc

            for (game_id, game), (payload, error) in zip(
                todo, pool.map(fetch_one, todo)
            ):
                try:
                    if error:
                        raise error
                    save_game(
                        db, index, game_id, game, payload
                    )
                    if payload["boxscore"] is None:
                        upcoming += 1
                    else:
                        imported += 1
                        done.add(game_id)
                except Exception as exc:
                    skipped += 1
                    print(
                        f"[SKIPPED] Game {game_id}: {exc}"
                    )

            if todo:
                print(
                    f"[{season}] {day}: {len(todo)} games saved."
                )

    print(
        f"[{season}] done: {len(seen)} games found,"
        f" {imported} results imported, {upcoming} upcoming,"
        f" {skipped} skipped, {failed_dates} dates failed."
    )
    season_over = dates[-1] + SEASON_OVER_AFTER < today
    return season_over and failed_dates == 0


# ---------- whole download ----------


def prepare_database(db_path=DB_PATH, today=None):
    """Create any missing tables.

    Returns True if there's anything to download (always true
    during a season, so new results get picked up).
    """
    today = today or date.today()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as db:
        ensure_schema(db)
        return bool(seasons_to_download(db, today))


def fill_database(
    db_path=DB_PATH,
    fetch=get_api_data,
    update=False,
    today=None,
):
    """Download every season that isn't finished yet.

    Anything interrupted (e.g. the app was closed partway)
    carries on next time, since saved games are skipped.
    """
    today = today or date.today()
    downloading.set()
    try:
        Path(db_path).parent.mkdir(
            parents=True, exist_ok=True
        )
        with closing(sqlite3.connect(db_path)) as db:
            ensure_schema(db)
            db.execute("PRAGMA foreign_keys = ON")

            merged = dedupe_players(db)
            if merged:
                print(
                    f"Merged {merged} duplicate player rows."
                )

            seasons = seasons_to_download(db, today, update)
            if not seasons:
                print(
                    f"Database is up to date ({game_count(db)}"
                    " games). Run with --update to re-check."
                )
                return

            # Today backwards through every season first,
            # then the upcoming games.
            for season in seasons:
                if scrape_season(
                    db, season, fetch, today, part="past"
                ):
                    mark_season_finished(db, season)
            for season in seasons:
                if season == current_season(today):
                    scrape_season(
                        db,
                        season,
                        fetch,
                        today,
                        part="future",
                    )
            print(
                f"Database: {db_path} ({game_count(db)} games)"
            )
    finally:
        downloading.clear()


def main(argv=None, db_path=DB_PATH, fetch=get_api_data):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="re-check seasons already marked finished",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="wipe the database and download everything again",
    )
    args = parser.parse_args(argv)
    if args.reset:
        reset_database(db_path)
        print("Database wiped.")
    fill_database(db_path, fetch=fetch, update=args.update)


if __name__ == "__main__":
    main()
