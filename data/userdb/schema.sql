create table IF NOT EXISTS User (
    user_name varchar(32),
    user_id int,
    pass varchar(256),

    primary key (user_id)
);

CREATE TABLE IF NOT EXISTS ChatSession (
    session_id int,
    user_id int,
    session_time DATETIME,

    primary key (session_id, user_id),
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ChatMessage (
    message_id int,
    session_id int,
    user_id int,
    agent_type varchar(4),
    message_text varchar(2048),

    PRIMARY KEY (message_id, session_id, user_id),
    FOREIGN KEY (session_id, user_id) REFERENCES ChatSession(session_id, user_id) ON DELETE CASCADE
);