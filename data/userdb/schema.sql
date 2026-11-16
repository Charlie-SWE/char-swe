create table IF NOT EXISTS User (
    user_id varchar(32),
    pass varchar(256),

    primary key (user_id)
);

CREATE TABLE IF NOT EXISTS ChatSession (
    session_id int,
    user_id varchar(32),

    primary key (session_id, user_id)
);

CREATE TABLE IF NOT EXISTS ChatMessage (
    message_id int,
    session_id int,
    user_id varchar(32),
    agent_type varchar(4),
    message_text varchar(2048),

    PRIMARY KEY (message_id, session_id, user_id)
);