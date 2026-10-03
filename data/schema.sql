PRAGMA foreign_keys = ON;

create table Teams (
    team_id integer primary key,
    team_name text not null
);

create table Players (
    player_id integer primary key,
    team_id integer not null,
    first_name text not null,
    last_name text not null,
    position text,
    jersey_number integer check (jersey_number >= 0),
    foreign key (team_id) references Teams(team_id)
);

create table Games (
    game_id integer primary key,
    game_date date not null,
    home_team_id integer not null,
    away_team_id integer not null,
    location text,
    home_score integer check (home_score >= 0),
    away_score integer check (away_score >= 0),
    weather text, 
    foreign key (home_team_id) references Teams(team_id),
    foreign key (away_team_id) references Teams(team_id)
);

create table PlayerGameStats (
    player_id integer not null,
    game_id integer not null,
    
    goals integer default 0,
    assists integer default 0,
    minutes_played real default 0,
    shots integer default 0,
    shots_on_goal integer default 0,

    penalty_shot_goals integer default 0,
    penalty_shot_attempts integer default 0

    fouls integer default 0,
    yellow_cards integer default 0,
    red_cards integer default 0,
    saves integer default 0,

    starter integer not null,
    participated integer not null,

    primary key (player_id, game_id),
    foreign key (player_id) references Players(player_id),
    foreign key (game_id) references Games(game_id)
);

-- create table TeamGameStats (
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

