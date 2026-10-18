-- Currently just for storing historical game 
-- and player data, will be updated

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS teams (
    team_id integer PRIMARY KEY,
    team_name text NOT NULL
);

CREATE TABLE IF NOT EXISTS players (
    player_id integer PRIMARY KEY,
    first_name text NOT NULL,
    last_name text NOT NULL,
    position text,
    jersey_number integer CHECK (jersey_number >= 0)
);

CREATE TABLE IF NOT EXISTS games (
    game_id integer PRIMARY KEY,
    game_date date NOT NULL,
    home_team_id integer NOT NULL,
    away_team_id integer NOT NULL,
    location text,
    home_score integer CHECK (home_score >= 0),
    away_score integer CHECK (away_score >= 0),
    weather text,
    FOREIGN KEY (home_team_id) REFERENCES teams (team_id),
    FOREIGN KEY (away_team_id) REFERENCES teams (team_id)
);

CREATE TABLE IF NOT EXISTS playergamestats (
    player_id integer NOT NULL,
    game_id integer NOT NULL,
    team_id integer NOT NULL,

    goals integer DEFAULT 0,
    assists integer DEFAULT 0,
    minutes_played real DEFAULT 0,
    shots integer DEFAULT 0,
    shots_on_goal integer DEFAULT 0,

    penalty_shot_goals integer DEFAULT 0,
    penalty_shot_attempts integer DEFAULT 0,

    fouls integer DEFAULT 0,
    yellow_cards integer DEFAULT 0,
    red_cards integer DEFAULT 0,
    saves integer DEFAULT 0,
    goals_against integer DEFAULT 0,

    starter integer NOT NULL,
    participated integer NOT NULL,

    PRIMARY KEY (player_id, game_id),
    FOREIGN KEY (player_id) REFERENCES players (player_id),
    FOREIGN KEY (game_id) REFERENCES games (game_id),
    FOREIGN KEY (team_id) REFERENCES teams (team_id)
);

-- create table if not exists TeamGameStats (
--     team_id integer not null,
--     game_id integer not null,

--     goals integer default 0,
--     assists integer default 0,
--     shots integer default 0,
--     shots_on_goal integer default 0,

--     penalty_shot_goals integer default 0,
--     penalty_shot_attempts integer default 0,

--     saves integer default 0,
--     fouls integer default 0,
--     corners integer default 0,
--     offsides integer default 0,

--     yellow_cards integer default 0,
--     red_cards integer default 0,

--     primary key (team_id, game_id),
--     foreign key (team_id) references Teams(team_id),
--     foreign key (game_id) references Games(game_id)
-- );
