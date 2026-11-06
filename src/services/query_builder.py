import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

DB_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "gaffer.db"
)

# Column name shown in the UI -> SQL expression.
COLUMNS = {
    "player_id": "p.player_id",
    "jersey_number": "p.jersey_number",
    "first_name": "p.first_name",
    "last_name": "p.last_name",
    "position": "p.position",
    "games": "COUNT(s.game_id)",
    "goals": "COALESCE(SUM(s.goals), 0)",
    "assists": "COALESCE(SUM(s.assists), 0)",
}

# The database stores positions inconsistently, so each
# dropdown choice matches every raw value that means it.
POSITION_GROUPS = {
    "GK": ["GK", "GOALKEEPER", "gk"],
    "D": [
        "D",
        "DEFENDER",
        "CENTERBACK",
        "LEFTBACK",
        "d",
        "def",
    ],
    "M": [
        "M",
        "MIDFIELDER",
        "CENTERMIDFIELD",
        "CENTERATTACKINGMIDFIELD",
        "CENTERDEFENSIVEMIDFIELD",
        "m",
        "mid",
    ],
    "F": [
        "F",
        "FORWARD",
        "STRIKER",
        "LEFTFORWARD",
        "RIGHTFORWARD",
        "LEFTWINGER",
        "RIGHTWINGER",
        "f",
        "fwd",
    ],
    "Unknown": ["n/a"],  # plus NULL, handled below
}


@dataclass
class PlayerFilters:
    columns: list[str] = field(
        default_factory=lambda: [
            "first_name",
            "last_name",
            "position",
            "goals",
            "assists",
        ]
    )
    name: str | None = None
    team_id: int | None = None
    position: str | None = None
    order_by: str = "last_name"
    descending: bool = False
    limit: int | None = None  # None = all matching rows


def _escape_like(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def build_player_query(
    f: PlayerFilters,
) -> tuple[str, list]:
    if not f.columns:
        raise ValueError("Pick at least one column")
    for col in f.columns + [f.order_by]:
        if col not in COLUMNS:
            raise ValueError(f"Unknown column: {col}")
    if f.limit is not None and (
        not isinstance(f.limit, int) or f.limit < 1
    ):
        raise ValueError("Limit must be a positive number")

    select = ", ".join(
        f"{COLUMNS[c]} AS {c}" for c in f.columns
    )
    sql = (
        f"SELECT {select} FROM Players p "
        "LEFT JOIN PlayerGameStats s "
        "ON s.player_id = p.player_id"
    )
    where = []
    params: list = []

    if f.name and f.name.strip():
        where.append(
            "(p.first_name || ' ' || p.last_name) "
            "LIKE ? ESCAPE '\\'"
        )
        params.append(f"%{_escape_like(f.name.strip())}%")

    if f.team_id is not None:
        if not isinstance(f.team_id, int):
            raise ValueError("Team id must be a number")
        where.append(
            "p.player_id IN (SELECT player_id "
            "FROM PlayerGameStats WHERE team_id = ?)"
        )
        params.append(f.team_id)

    if f.position is not None:
        if f.position not in POSITION_GROUPS:
            raise ValueError(
                f"Unknown position: {f.position}"
            )
        values = POSITION_GROUPS[f.position]
        marks = ", ".join("?" for _ in values)
        clause = f"p.position IN ({marks})"
        if f.position == "Unknown":
            clause = f"(p.position IS NULL OR {clause})"
        where.append(clause)
        params.extend(values)

    if where:
        sql += " WHERE " + " AND ".join(where)

    direction = "DESC" if f.descending else "ASC"
    sql += (
        " GROUP BY p.player_id"
        f" ORDER BY {COLUMNS[f.order_by]} {direction}"
    )
    if f.limit is not None:
        sql += " LIMIT ?"
        params.append(f.limit)
    return sql, params


def run_query(
    conn: sqlite3.Connection, sql: str, params: list
) -> list[dict]:
    conn.row_factory = sqlite3.Row
    return [dict(row) for row in conn.execute(sql, params)]


def list_teams(conn: sqlite3.Connection) -> dict[int, str]:
    rows = conn.execute(
        "SELECT team_id, team_name FROM Teams "
        "ORDER BY team_name"
    )
    return {team_id: name for team_id, name in rows}
